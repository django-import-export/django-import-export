from decimal import Decimal
from unittest import mock

import tablib
from core.models import Book
from core.tests.resources import BookResource, BookResourceWithStoreInstance
from django.db import connections
from django.test import TestCase, skipUnlessDBFeature

from import_export import results
from import_export.resources import Diff


class DataImportTests(TestCase):
    def setUp(self):
        self.resource = BookResource()
        self.book = Book.objects.create(name="Some book")
        self.dataset = tablib.Dataset(headers=["id", "name", "author_email", "price"])
        row = [self.book.pk, "Some book", "test@example.com", "10.25"]
        self.dataset.append(row)

    def test_get_diff(self):
        diff = Diff(self.resource, self.book, False)
        book2 = Book(name="Some other book")
        diff.compare_with(self.resource, book2)
        html = diff.as_html()
        headers = self.resource.get_export_headers()
        self.assertEqual(
            html[headers.index("name")],
            '<span>Some </span><ins style="background:#e6ffe6;">'
            "other </ins><span>book</span>",
        )
        self.assertFalse(html[headers.index("author_email")])

    def test_import_data_update(self):
        result = self.resource.import_data(self.dataset, raise_errors=True)

        self.assertFalse(result.has_errors())
        self.assertEqual(len(result.rows), 1)
        self.assertTrue(result.rows[0].diff)
        self.assertEqual(
            result.rows[0].import_type, results.RowResult.IMPORT_TYPE_UPDATE
        )
        self.assertEqual(result.rows[0].row_values.get("name"), None)
        self.assertEqual(result.rows[0].row_values.get("author_email"), None)

        self.assertIsNone(result.rows[0].instance)
        self.assertIsNotNone(result.rows[0].original)

        instance = Book.objects.get(pk=self.book.pk)
        self.assertEqual(instance.author_email, "test@example.com")
        self.assertEqual(instance.price, Decimal("10.25"))

    def test_import_data_new(self):
        Book.objects.all().delete()
        self.assertEqual(0, Book.objects.count())
        result = self.resource.import_data(self.dataset, raise_errors=True)

        self.assertFalse(result.has_errors())
        self.assertEqual(len(result.rows), 1)
        self.assertTrue(result.rows[0].diff)
        self.assertEqual(result.rows[0].import_type, results.RowResult.IMPORT_TYPE_NEW)
        self.assertEqual(result.rows[0].row_values.get("name"), None)
        self.assertEqual(result.rows[0].row_values.get("author_email"), None)

        self.assertIsNone(result.rows[0].instance)
        self.assertIsNone(result.rows[0].original)

        self.assertEqual(1, Book.objects.count())
        instance = Book.objects.first()
        self.assertEqual(instance.author_email, "test@example.com")
        self.assertEqual(instance.price, Decimal("10.25"))

    def test_import_data_new_store_instance(self):
        self.resource = BookResourceWithStoreInstance()
        Book.objects.all().delete()
        self.assertEqual(0, Book.objects.count())
        result = self.resource.import_data(self.dataset, raise_errors=True)

        self.assertEqual(result.rows[0].import_type, results.RowResult.IMPORT_TYPE_NEW)
        self.assertIsNotNone(result.rows[0].instance)
        self.assertIsNone(result.rows[0].original)
        self.assertEqual(1, Book.objects.count())
        book = Book.objects.first()
        self.assertEqual(book.pk, result.rows[0].instance.pk)

    def test_import_data_update_store_instance(self):
        self.resource = BookResourceWithStoreInstance()
        result = self.resource.import_data(self.dataset, raise_errors=True)
        self.assertEqual(
            result.rows[0].import_type, results.RowResult.IMPORT_TYPE_UPDATE
        )
        self.assertIsNotNone(result.rows[0].instance)
        self.assertIsNotNone(result.rows[0].original)
        self.assertEqual(1, Book.objects.count())
        book = Book.objects.first()
        self.assertEqual(book.pk, result.rows[0].instance.pk)

    @skipUnlessDBFeature("supports_transactions")
    @mock.patch("import_export.resources.connections")
    def test_import_data_no_transaction(self, mock_db_connections):
        class Features:
            supports_transactions = False

        class DummyConnection:
            features = Features()

        dummy_connection = DummyConnection()
        mock_db_connections.__getitem__.return_value = dummy_connection
        result = self.resource.import_data(
            self.dataset, dry_run=True, use_transactions=False, raise_errors=True
        )

        self.assertFalse(result.has_errors())
        self.assertEqual(len(result.rows), 1)
        self.assertTrue(result.rows[0].diff)
        self.assertEqual(
            result.rows[0].import_type, results.RowResult.IMPORT_TYPE_UPDATE
        )
        self.assertEqual(result.rows[0].row_values.get("name"), None)
        self.assertEqual(result.rows[0].row_values.get("author_email"), None)

    def test_import_data_new_override_do_instance_save(self):
        class CustomDoInstanceSave(BookResource):
            is_create = False

            def do_instance_save(self, instance, is_create):
                self.is_create = is_create
                super().do_instance_save(instance, is_create)

        Book.objects.all().delete()
        self.assertEqual(0, Book.objects.count())
        self.resource = CustomDoInstanceSave()
        self.assertFalse(self.resource.is_create)

        result = self.resource.import_data(self.dataset, raise_errors=True)

        self.assertFalse(result.has_errors())
        self.assertEqual(1, Book.objects.count())
        self.assertTrue(self.resource.is_create)


class SequenceResetTests(TestCase):
    """
    ``ModelResource.after_import()`` resets the model's pk sequence to support
    fixture-style imports which supply explicit pk values.  When imported rows
    do not supply pk values the reset serves no purpose and, on PostgreSQL, can
    rewind the shared sequence under concurrent imports, causing
    ``IntegrityError`` on inserts in a concurrent import of the same model
    (#2166).  The reset must therefore only run when a created row supplied an
    explicit pk.
    """

    def setUp(self):
        self.resource = BookResource()
        connection_name = self.resource.get_db_connection_name()
        self.connection = connections[connection_name]

    def import_with_mocked_reset(self, dataset, resource=None, **kwargs):
        resource = resource or self.resource
        with mock.patch.object(
            self.connection.ops, "sequence_reset_sql", return_value=[]
        ) as mock_reset:
            result = resource.import_data(dataset, raise_errors=True, **kwargs)
        return result, mock_reset

    def test_no_reset_when_created_rows_supply_no_pk(self):
        dataset = tablib.Dataset(headers=["id", "name"])
        dataset.append(["", "Some book"])

        result, mock_reset = self.import_with_mocked_reset(dataset)

        self.assertEqual(results.RowResult.IMPORT_TYPE_NEW, result.rows[0].import_type)
        mock_reset.assert_not_called()

    def test_reset_when_created_rows_supply_pk(self):
        # fixture-style import: the data supplies explicit pk values
        dataset = tablib.Dataset(headers=["id", "name"])
        dataset.append([101, "Some book"])

        result, mock_reset = self.import_with_mocked_reset(dataset)

        self.assertEqual(results.RowResult.IMPORT_TYPE_NEW, result.rows[0].import_type)
        mock_reset.assert_called_once()

    def test_no_reset_when_created_rows_supply_no_pk_use_bulk(self):
        class BulkBookResource(BookResource):
            class Meta:
                model = Book
                use_bulk = True

        dataset = tablib.Dataset(headers=["id", "name"])
        dataset.append(["", "Some book"])

        result, mock_reset = self.import_with_mocked_reset(
            dataset, resource=BulkBookResource()
        )

        self.assertEqual(results.RowResult.IMPORT_TYPE_NEW, result.rows[0].import_type)
        self.assertEqual(1, Book.objects.count())
        mock_reset.assert_not_called()

    def test_reset_when_created_rows_supply_pk_use_bulk(self):
        class BulkBookResource(BookResource):
            class Meta:
                model = Book
                use_bulk = True

        dataset = tablib.Dataset(headers=["id", "name"])
        dataset.append([101, "Some book"])

        result, mock_reset = self.import_with_mocked_reset(
            dataset, resource=BulkBookResource()
        )

        self.assertEqual(results.RowResult.IMPORT_TYPE_NEW, result.rows[0].import_type)
        self.assertEqual(1, Book.objects.count())
        mock_reset.assert_called_once()

    def test_reused_resource_does_not_reset_on_later_import_without_pk(self):
        # the flag tracking supplied pks must be re-initialized per import run
        dataset_with_pk = tablib.Dataset(headers=["id", "name"])
        dataset_with_pk.append([101, "Some book"])
        _, mock_reset = self.import_with_mocked_reset(dataset_with_pk)
        mock_reset.assert_called_once()

        dataset_without_pk = tablib.Dataset(headers=["id", "name"])
        dataset_without_pk.append(["", "Some other book"])
        _, mock_reset = self.import_with_mocked_reset(dataset_without_pk)
        mock_reset.assert_not_called()
