from decimal import Decimal
from unittest import mock

import tablib
from core.models import Book
from core.tests.resources import BookResource, BookResourceWithStoreInstance
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
