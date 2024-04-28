from unittest import mock

import tablib
from core.models import Book, UUIDBook
from django.core.exceptions import ValidationError
from django.test import TestCase

from import_export import exceptions, fields, resources, widgets
from import_export.instance_loaders import ModelInstanceLoader


class BulkTest(TestCase):
    def setUp(self):
        class _BookResource(resources.ModelResource):
            class Meta:
                model = Book
                use_bulk = True

        self.resource = _BookResource()
        rows = [(i + 1, "book_name") for i in range(10)]
        self.dataset = tablib.Dataset(*rows, headers=["id", "name"])

    def init_update_test_data(self, model=Book):
        [model.objects.create(name="book_name") for _ in range(10)]
        self.assertEqual(10, model.objects.count())
        rows = model.objects.all().values_list("id", "name")
        updated_rows = [(r[0], "UPDATED") for r in rows]
        self.dataset = tablib.Dataset(*updated_rows, headers=["id", "name"])


class BulkCreateTest(BulkTest):
    @mock.patch("core.models.Book.objects.bulk_create")
    def test_bulk_create_does_not_call_object_save(self, mock_bulk_create):
        with mock.patch("core.models.Book.save") as mock_obj_save:
            self.resource.import_data(self.dataset)
            mock_obj_save.assert_not_called()
        mock_bulk_create.assert_called_with(mock.ANY, batch_size=None)

    @mock.patch("core.models.Book.objects.bulk_create")
    def test_bulk_create_batch_size_of_5(self, mock_bulk_create):
        class _BookResource(resources.ModelResource):
            class Meta:
                model = Book
                use_bulk = True
                batch_size = 5

        resource = _BookResource()
        result = resource.import_data(self.dataset)
        self.assertEqual(2, mock_bulk_create.call_count)
        mock_bulk_create.assert_called_with(mock.ANY, batch_size=5)
        self.assertEqual(10, result.total_rows)

    @mock.patch("core.models.UUIDBook.objects.bulk_create")
    def test_bulk_create_uuid_model(self, mock_bulk_create):
        """Test create of a Model which defines uuid not pk (issue #1274)"""

        class _UUIDBookResource(resources.ModelResource):
            class Meta:
                model = UUIDBook
                use_bulk = True
                batch_size = 5
                fields = (
                    "id",
                    "name",
                )

        resource = _UUIDBookResource()
        result = resource.import_data(self.dataset)
        self.assertEqual(2, mock_bulk_create.call_count)
        mock_bulk_create.assert_called_with(mock.ANY, batch_size=5)
        self.assertEqual(10, result.total_rows)

    @mock.patch("core.models.Book.objects.bulk_create")
    def test_bulk_create_no_batch_size(self, mock_bulk_create):
        class _BookResource(resources.ModelResource):
            class Meta:
                model = Book
                use_bulk = True
                batch_size = None

        resource = _BookResource()
        result = resource.import_data(self.dataset)
        self.assertEqual(1, mock_bulk_create.call_count)
        mock_bulk_create.assert_called_with(mock.ANY, batch_size=None)
        self.assertEqual(10, result.total_rows)
        self.assertEqual(10, result.totals["new"])

    @mock.patch("core.models.Book.objects.bulk_create")
    def test_bulk_create_called_dry_run(self, mock_bulk_create):
        class _BookResource(resources.ModelResource):
            class Meta:
                model = Book
                use_bulk = True
                batch_size = None

        resource = _BookResource()
        result = resource.import_data(self.dataset, dry_run=True)
        self.assertEqual(1, mock_bulk_create.call_count)
        self.assertEqual(10, result.total_rows)
        self.assertEqual(10, result.totals["new"])

    @mock.patch("core.models.Book.objects.bulk_create")
    def test_bulk_create_not_called_when_not_using_transactions(self, mock_bulk_create):
        class _BookResource(resources.ModelResource):
            def import_data(
                self,
                dataset,
                dry_run=False,
                raise_errors=False,
                use_transactions=None,
                collect_failed_rows=False,
                **kwargs,
            ):
                # override so that we can enforce not using_transactions
                using_transactions = False
                return self.import_data_inner(
                    dataset,
                    dry_run,
                    raise_errors,
                    using_transactions,
                    collect_failed_rows,
                    **kwargs,
                )

            class Meta:
                model = Book
                use_bulk = True

        resource = _BookResource()
        resource.import_data(self.dataset, dry_run=True)
        mock_bulk_create.assert_not_called()

    @mock.patch("core.models.Book.objects.bulk_create")
    def test_bulk_create_batch_size_of_4(self, mock_bulk_create):
        class _BookResource(resources.ModelResource):
            class Meta:
                model = Book
                use_bulk = True
                batch_size = 4

        resource = _BookResource()
        result = resource.import_data(self.dataset)
        self.assertEqual(3, mock_bulk_create.call_count)
        self.assertEqual(10, result.total_rows)
        self.assertEqual(10, result.totals["new"])

    def test_no_changes_for_errors_if_use_transactions_enabled(self):
        with mock.patch("import_export.results.Result.has_errors") as mock_has_errors:
            mock_has_errors.return_val = True
            self.resource.import_data(self.dataset)
        self.assertEqual(0, Book.objects.count())

    @mock.patch("core.models.Book.objects.bulk_create")
    def test_bulk_create_use_bulk_disabled(self, mock_bulk_create):
        class _BookResource(resources.ModelResource):
            class Meta:
                model = Book
                use_bulk = False

        resource = _BookResource()
        result = resource.import_data(self.dataset)
        mock_bulk_create.assert_not_called()
        self.assertEqual(10, Book.objects.count())
        self.assertEqual(10, result.total_rows)
        self.assertEqual(10, result.totals["new"])

    @mock.patch("core.models.Book.objects.bulk_create")
    def test_bulk_create_bad_batch_size_value(self, mock_bulk_create):
        class _BookResource(resources.ModelResource):
            class Meta:
                model = Book
                use_bulk = True
                batch_size = "a"

        resource = _BookResource()
        with self.assertRaises(ValueError):
            resource.import_data(self.dataset)
        mock_bulk_create.assert_not_called()

    @mock.patch("core.models.Book.objects.bulk_create")
    def test_bulk_create_negative_batch_size_value(self, mock_bulk_create):
        class _BookResource(resources.ModelResource):
            class Meta:
                model = Book
                use_bulk = True
                batch_size = -1

        resource = _BookResource()
        with self.assertRaises(ValueError):
            resource.import_data(self.dataset)
        mock_bulk_create.assert_not_called()

    @mock.patch("core.models.Book.objects.bulk_create")
    def test_bulk_create_oversized_batch_size_value(self, mock_bulk_create):
        class _BookResource(resources.ModelResource):
            class Meta:
                model = Book
                use_bulk = True
                batch_size = 100

        resource = _BookResource()
        result = resource.import_data(self.dataset)
        self.assertEqual(1, mock_bulk_create.call_count)
        mock_bulk_create.assert_called_with(mock.ANY, batch_size=None)
        self.assertEqual(10, result.total_rows)
        self.assertEqual(10, result.totals["new"])

    @mock.patch("core.models.Book.objects.bulk_create")
    def test_bulk_create_logs_exception(self, mock_bulk_create):
        e = ValidationError("invalid field")
        mock_bulk_create.side_effect = e

        class _BookResource(resources.ModelResource):
            class Meta:
                model = Book
                use_bulk = True
                batch_size = 100

        resource = _BookResource()
        with mock.patch("logging.Logger.debug") as mock_exception:
            resource.import_data(self.dataset)
            mock_exception.assert_called_with(e, exc_info=e)

    @mock.patch("core.models.Book.objects.bulk_create")
    def test_bulk_create_raises_exception(self, mock_bulk_create):
        mock_bulk_create.side_effect = ValidationError("invalid field")

        class _BookResource(resources.ModelResource):
            class Meta:
                model = Book
                use_bulk = True
                batch_size = 100

        resource = _BookResource()
        with self.assertRaises(exceptions.ImportError):
            resource.import_data(self.dataset, raise_errors=True)

    @mock.patch("core.models.Book.objects.bulk_create")
    def test_bulk_create_exception_gathered_on_dry_run(self, mock_bulk_create):
        mock_bulk_create.side_effect = ValidationError("invalid field")

        class _BookResource(resources.ModelResource):
            class Meta:
                model = Book
                use_bulk = True
                batch_size = 100

        resource = _BookResource()
        result = resource.import_data(self.dataset, dry_run=True, raise_errors=False)
        self.assertTrue(result.has_errors())

    def test_m2m_not_called_for_bulk(self):
        mock_m2m_widget = mock.Mock(spec=widgets.ManyToManyWidget)

        class BookM2MResource(resources.ModelResource):
            categories = fields.Field(attribute="categories", widget=mock_m2m_widget)

            class Meta:
                model = Book
                use_bulk = True

        resource = BookM2MResource()
        self.dataset.append_col(["Cat 1|Cat 2"] * 10, header="categories")
        resource.import_data(self.dataset, raise_errors=True)
        mock_m2m_widget.assert_not_called()

    def test_force_init_instance(self):
        class _BookResource(resources.ModelResource):
            def get_instance(self, instance_loader, row):
                raise AssertionError("should not be called")

            class Meta:
                model = Book
                force_init_instance = True

        resource = _BookResource()
        self.assertIsNotNone(
            resource.get_or_init_instance(
                ModelInstanceLoader(resource), self.dataset[0]
            )
        )

    @mock.patch("import_export.resources.atomic_if_using_transaction")
    def test_no_sub_transaction_on_row_for_bulk(self, mock_atomic_if_using_transaction):
        class _BookResource(resources.ModelResource):
            class Meta:
                model = Book
                use_bulk = True

        resource = _BookResource()
        resource.import_data(self.dataset)
        self.assertIn(
            False, [x[0][0] for x in mock_atomic_if_using_transaction.call_args_list]
        )


class BulkUpdateTest(BulkTest):
    class _BookResource(resources.ModelResource):
        class Meta:
            model = Book
            use_bulk = True
            fields = ("id", "name")
            import_id_fields = ("id",)

    def setUp(self):
        super().setUp()
        self.init_update_test_data()
        self.resource = self._BookResource()

    def test_bulk_update(self):
        result = self.resource.import_data(self.dataset)
        [self.assertEqual("UPDATED", b.name) for b in Book.objects.all()]
        self.assertEqual(10, result.total_rows)
        self.assertEqual(10, result.totals["update"])

    @mock.patch("core.models.Book.objects.bulk_update")
    def test_bulk_update_batch_size_of_4(self, mock_bulk_update):
        class _BookResource(resources.ModelResource):
            class Meta:
                model = Book
                use_bulk = True
                batch_size = 4

        resource = _BookResource()
        result = resource.import_data(self.dataset)
        self.assertEqual(3, mock_bulk_update.call_count)
        self.assertEqual(10, result.total_rows)
        self.assertEqual(10, result.totals["update"])

    @mock.patch("core.models.Book.objects.bulk_update")
    def test_bulk_update_batch_size_of_5(self, mock_bulk_update):
        class _BookResource(resources.ModelResource):
            class Meta:
                model = Book
                use_bulk = True
                batch_size = 5

        resource = _BookResource()
        result = resource.import_data(self.dataset)
        self.assertEqual(2, mock_bulk_update.call_count)
        self.assertEqual(10, result.total_rows)
        self.assertEqual(10, result.totals["update"])

    @mock.patch("core.models.Book.objects.bulk_update")
    def test_bulk_update_no_batch_size(self, mock_bulk_update):
        class _BookResource(resources.ModelResource):
            class Meta:
                model = Book
                use_bulk = True
                batch_size = None

        resource = _BookResource()
        result = resource.import_data(self.dataset)
        self.assertEqual(1, mock_bulk_update.call_count)
        mock_bulk_update.assert_called_with(mock.ANY, mock.ANY, batch_size=None)
        self.assertEqual(10, result.total_rows)
        self.assertEqual(10, result.totals["update"])

    @mock.patch("core.models.Book.objects.bulk_update")
    def test_bulk_update_not_called_when_not_using_transactions(self, mock_bulk_update):
        class _BookResource(resources.ModelResource):
            def import_data(
                self,
                dataset,
                dry_run=False,
                raise_errors=False,
                use_transactions=None,
                collect_failed_rows=False,
                **kwargs,
            ):
                # override so that we can enforce not using_transactions
                using_transactions = False
                return self.import_data_inner(
                    dataset,
                    dry_run,
                    raise_errors,
                    using_transactions,
                    collect_failed_rows,
                    **kwargs,
                )

            class Meta:
                model = Book
                use_bulk = True

        resource = _BookResource()
        resource.import_data(self.dataset, dry_run=True)
        mock_bulk_update.assert_not_called()

    @mock.patch("core.models.Book.objects.bulk_update")
    def test_bulk_update_called_for_dry_run(self, mock_bulk_update):
        self.resource.import_data(self.dataset, dry_run=True)
        self.assertEqual(1, mock_bulk_update.call_count)

    @mock.patch("core.models.Book.objects.bulk_update")
    def test_bulk_not_called_when_use_bulk_disabled(self, mock_bulk_update):
        class _BookResource(resources.ModelResource):
            class Meta:
                model = Book
                use_bulk = False

        resource = _BookResource()
        result = resource.import_data(self.dataset)
        self.assertEqual(10, Book.objects.count())
        self.assertEqual(10, result.total_rows)
        self.assertEqual(10, result.totals["update"])
        mock_bulk_update.assert_not_called()

    @mock.patch("core.models.Book.objects.bulk_update")
    def test_bulk_update_logs_exception(self, mock_bulk_update):
        e = ValidationError("invalid field")
        mock_bulk_update.side_effect = e

        class _BookResource(resources.ModelResource):
            class Meta:
                model = Book
                use_bulk = True

        resource = _BookResource()
        with mock.patch("logging.Logger.debug") as mock_exception:
            resource.import_data(self.dataset)
            mock_exception.assert_called_with(e, exc_info=e)

    @mock.patch("core.models.Book.objects.bulk_update")
    def test_bulk_update_raises_exception(self, mock_bulk_update):
        e = ValidationError("invalid field")
        mock_bulk_update.side_effect = e

        class _BookResource(resources.ModelResource):
            class Meta:
                model = Book
                use_bulk = True

        resource = _BookResource()
        with self.assertRaises(exceptions.ImportError) as raised_exc:
            resource.import_data(self.dataset, raise_errors=True)
            self.assertEqual(e, raised_exc)


class BulkUUIDBookUpdateTest(BulkTest):
    def setUp(self):
        super().setUp()
        self.init_update_test_data(model=UUIDBook)

    @mock.patch("core.models.UUIDBook.objects.bulk_update")
    def test_bulk_update_uuid_model(self, mock_bulk_update):
        """Test update of a Model which defines uuid not pk (issue #1274)"""

        class _UUIDBookResource(resources.ModelResource):
            class Meta:
                model = UUIDBook
                use_bulk = True
                batch_size = 5
                fields = (
                    "id",
                    "name",
                )

        resource = _UUIDBookResource()
        result = resource.import_data(self.dataset)
        self.assertEqual(2, mock_bulk_update.call_count)
        self.assertEqual(10, result.total_rows)
        self.assertEqual(10, result.totals["update"])


class BulkDeleteTest(BulkTest):
    class DeleteBookResource(resources.ModelResource):
        def for_delete(self, row, instance):
            return True

        class Meta:
            model = Book
            use_bulk = True
            # there are errors when diffing with mocks
            # therefore disable diff with this flag
            skip_diff = True

    def setUp(self):
        super().setUp()
        self.resource = self.DeleteBookResource()
        self.resource._meta.batch_size = 1000
        self.resource._meta.use_bulk = True
        self.init_update_test_data()

    @mock.patch("core.models.Book.delete")
    def test_bulk_delete_use_bulk_is_false(self, mock_obj_delete):
        self.resource._meta.use_bulk = False
        self.resource.import_data(self.dataset)
        self.assertEqual(10, mock_obj_delete.call_count)

    @mock.patch("core.models.Book.objects")
    def test_bulk_delete_batch_size_of_4(self, mock_obj_manager):
        self.resource._meta.batch_size = 4
        result = self.resource.import_data(self.dataset)
        self.assertEqual(3, mock_obj_manager.filter.return_value.delete.call_count)
        self.assertEqual(10, result.total_rows)
        self.assertEqual(10, result.totals["delete"])

    @mock.patch("core.models.Book.objects")
    def test_bulk_delete_batch_size_of_5(self, mock_obj_manager):
        self.resource._meta.batch_size = 5
        result = self.resource.import_data(self.dataset)
        self.assertEqual(2, mock_obj_manager.filter.return_value.delete.call_count)
        self.assertEqual(10, result.total_rows)
        self.assertEqual(10, result.totals["delete"])

    @mock.patch("core.models.Book.objects")
    def test_bulk_delete_batch_size_is_none(self, mock_obj_manager):
        self.resource._meta.batch_size = None
        result = self.resource.import_data(self.dataset)
        self.assertEqual(1, mock_obj_manager.filter.return_value.delete.call_count)
        self.assertEqual(10, result.total_rows)
        self.assertEqual(10, result.totals["delete"])

    @mock.patch("core.models.Book.objects")
    def test_bulk_delete_not_called_when_not_using_transactions(self, mock_obj_manager):
        class _BookResource(self.DeleteBookResource):
            def import_data(
                self,
                dataset,
                dry_run=False,
                raise_errors=False,
                use_transactions=None,
                collect_failed_rows=False,
                **kwargs,
            ):
                # override so that we can enforce not using_transactions
                using_transactions = False
                return self.import_data_inner(
                    dataset,
                    dry_run,
                    raise_errors,
                    using_transactions,
                    collect_failed_rows,
                    **kwargs,
                )

        resource = _BookResource()
        resource.import_data(self.dataset, dry_run=True)
        self.assertEqual(0, mock_obj_manager.filter.return_value.delete.call_count)

    @mock.patch("core.models.Book.objects")
    def test_bulk_delete_called_for_dry_run(self, mock_obj_manager):
        self.resource.import_data(self.dataset, dry_run=True)
        self.assertEqual(1, mock_obj_manager.filter.return_value.delete.call_count)

    @mock.patch("core.models.Book.objects")
    def test_bulk_delete_logs_exception(self, mock_obj_manager):
        e = Exception("invalid")
        mock_obj_manager.filter.return_value.delete.side_effect = e

        with mock.patch("logging.Logger.debug") as mock_exception:
            self.resource.import_data(self.dataset)
            mock_exception.assert_called_with(e, exc_info=mock.ANY)
            self.assertEqual(1, mock_exception.call_count)

    @mock.patch("core.models.Book.objects")
    def test_bulk_delete_raises_exception(self, mock_obj_manager):
        e = Exception("invalid")
        mock_obj_manager.filter.return_value.delete.side_effect = e

        with self.assertRaises(Exception) as raised_exc:
            self.resource.import_data(self.dataset, raise_errors=True)
            self.assertEqual(e, raised_exc)


class BulkUUIDBookDeleteTest(BulkTest):
    class DeleteBookResource(resources.ModelResource):
        def for_delete(self, row, instance):
            return True

        class Meta:
            model = UUIDBook
            use_bulk = True
            batch_size = 5

    def setUp(self):
        super().setUp()
        self.resource = self.DeleteBookResource()
        self.init_update_test_data(model=UUIDBook)

    def test_bulk_delete_batch_size_of_5(self):
        self.assertEqual(10, UUIDBook.objects.count())
        self.resource.import_data(self.dataset)
        self.assertEqual(0, UUIDBook.objects.count())
