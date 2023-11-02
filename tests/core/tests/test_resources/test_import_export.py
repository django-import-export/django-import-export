from unittest.mock import patch

import tablib
from core.models import Book
from core.tests.resources import BookResource
from core.tests.utils import ignore_widget_deprecation_warning
from django.test import TestCase

from import_export import exceptions, fields, resources


class AfterImportComparisonTest(TestCase):
    class BookResource(resources.ModelResource):
        is_published = False

        def after_import_row(self, row, row_result, **kwargs):
            if (
                getattr(row_result.original, "published") is None
                and getattr(row_result.instance, "published") is not None
            ):
                self.is_published = True

        class Meta:
            model = Book
            store_instance = True

    def setUp(self):
        super().setUp()
        self.resource = AfterImportComparisonTest.BookResource()
        self.book = Book.objects.create(name="Some book")
        self.dataset = tablib.Dataset(headers=["id", "name", "published"])
        row = [self.book.pk, "Some book", "2023-05-09"]
        self.dataset.append(row)

    @ignore_widget_deprecation_warning
    def test_after_import_row_check_for_change(self):
        # issue 1583 - assert that `original` object is available to after_import_row()
        self.resource.import_data(self.dataset, raise_errors=True)
        self.assertTrue(self.resource.is_published)


class ImportExportFieldOrderTest(TestCase):
    class BaseBookResource(resources.ModelResource):
        def __init__(self):
            self.field_names = list()

        def get_queryset(self):
            return Book.objects.all().order_by("id")

        def import_field(self, field, obj, data, is_m2m=False, **kwargs):
            # mock out import_field() so that we can see the order
            # fields were called
            self.field_names.append(field.column_name)

    class UnorderedBookResource(BaseBookResource):
        class Meta:
            fields = ("price", "id", "name")
            model = Book

    class OrderedBookResource(BaseBookResource):
        class Meta:
            fields = ("price", "id", "name")
            import_order = ("price", "name", "id")
            export_order = ("price", "name", "id")
            model = Book

    class SubsetOrderedBookResource(BaseBookResource):
        class Meta:
            fields = ("price", "id", "name", "published")
            import_order = ("name",)
            export_order = ("published",)
            model = Book

    class DuplicateFieldsBookResource(BaseBookResource):
        class Meta:
            fields = ("id", "price", "name", "price")
            model = Book

    class FieldsAsListBookResource(BaseBookResource):
        class Meta:
            fields = ["id", "price", "name"]
            model = Book

    def setUp(self):
        super().setUp()
        self.pk = Book.objects.create(name="Ulysses", price="1.99").pk
        self.dataset = tablib.Dataset(headers=["id", "name", "price"])
        row = [self.pk, "Some book", "19.99"]
        self.dataset.append(row)

    @ignore_widget_deprecation_warning
    def test_defined_import_order(self):
        self.resource = ImportExportFieldOrderTest.OrderedBookResource()
        self.resource.import_data(self.dataset)
        self.assertEqual(["price", "name", "id"], self.resource.field_names)

    @ignore_widget_deprecation_warning
    def test_undefined_import_order(self):
        self.resource = ImportExportFieldOrderTest.UnorderedBookResource()
        self.resource.import_data(self.dataset)
        self.assertEqual(["price", "id", "name"], self.resource.field_names)

    @ignore_widget_deprecation_warning
    def test_defined_export_order(self):
        self.resource = ImportExportFieldOrderTest.OrderedBookResource()
        data = self.resource.export()
        target = f"price,name,id\r\n1.99,Ulysses,{self.pk}\r\n"
        self.assertEqual(target, data.csv)

    @ignore_widget_deprecation_warning
    def test_undefined_export_order(self):
        # When export order is not defined,
        # exported order should correspond with 'fields' definition
        self.resource = ImportExportFieldOrderTest.UnorderedBookResource()
        data = self.resource.export()
        target = f"price,id,name\r\n1.99,{self.pk},Ulysses\r\n"
        self.assertEqual(target, data.csv)

    @ignore_widget_deprecation_warning
    def test_subset_import_order(self):
        self.resource = ImportExportFieldOrderTest.SubsetOrderedBookResource()
        self.resource.import_data(self.dataset)
        self.assertEqual(
            ["name", "price", "id", "published"], self.resource.field_names
        )

    @ignore_widget_deprecation_warning
    def test_subset_export_order(self):
        self.resource = ImportExportFieldOrderTest.SubsetOrderedBookResource()
        data = self.resource.export()
        target = f"published,price,id,name\r\n,1.99,{self.pk},Ulysses\r\n"
        self.assertEqual(target, data.csv)

    @ignore_widget_deprecation_warning
    def test_duplicate_import_order(self):
        self.resource = ImportExportFieldOrderTest.DuplicateFieldsBookResource()
        self.resource.import_data(self.dataset)
        self.assertEqual(["id", "price", "name"], self.resource.field_names)

    @ignore_widget_deprecation_warning
    def test_duplicate_export_order(self):
        self.resource = ImportExportFieldOrderTest.DuplicateFieldsBookResource()
        data = self.resource.export()
        target = f"id,price,name\r\n{self.pk},1.99,Ulysses\r\n"
        self.assertEqual(target, data.csv)

    @ignore_widget_deprecation_warning
    def test_fields_as_list_import_order(self):
        self.resource = ImportExportFieldOrderTest.FieldsAsListBookResource()
        self.resource.import_data(self.dataset)
        self.assertEqual(["id", "price", "name"], self.resource.field_names)

    @ignore_widget_deprecation_warning
    def test_fields_as_list_export_order(self):
        self.resource = ImportExportFieldOrderTest.FieldsAsListBookResource()
        data = self.resource.export()
        target = f"id,price,name\r\n{self.pk},1.99,Ulysses\r\n"
        self.assertEqual(target, data.csv)


class ImportIdFieldsTestCase(TestCase):
    class BookResource(resources.ModelResource):
        name = fields.Field(attribute="name", column_name="book_name")

        class Meta:
            model = Book
            import_id_fields = ["name"]

    def setUp(self):
        super().setUp()
        self.book = Book.objects.create(name="The Hobbit")
        self.resource = ImportIdFieldsTestCase.BookResource()

    def test_custom_column_name_warns_if_not_present(self):
        dataset = tablib.Dataset(
            *[(self.book.pk, "Some book")], headers=["id", "wrong_name"]
        )
        with self.assertRaisesRegex(
            exceptions.FieldError,
            "The following import_id_fields are not present "
            "in the dataset: book_name",
        ):
            self.resource.import_data(dataset)

    def test_multiple_import_id_fields(self):
        class BookResource(resources.ModelResource):
            class Meta:
                model = Book
                import_id_fields = ("id", "name", "author_email")

        self.resource = BookResource()
        dataset = tablib.Dataset(
            *[(self.book.pk, "Goldeneye", "ian.fleming@example.com")],
            headers=["A", "name", "B"],
        )
        with self.assertRaisesRegex(
            exceptions.FieldError,
            "The following import_id_fields are not present "
            "in the dataset: id, author_email",
        ):
            self.resource.import_data(dataset)


class ImportWithMissingFields(TestCase):
    # issue 1517

    @patch("import_export.resources.logger")
    @patch("import_export.fields.Field.save")
    @ignore_widget_deprecation_warning
    def test_import_with_missing_instance_attribute(self, mock_field_save, mock_logger):
        class _BookResource(resources.ModelResource):
            name = fields.Field(column_name="name")

            class Meta:
                model = Book

        dataset = tablib.Dataset(*[(1, "Some book")], headers=["id", "name"])
        self.resource = _BookResource()
        result = self.resource.import_data(dataset)
        self.assertFalse(result.has_errors())
        target = (
            "skipping field '<import_export.fields.Field: name>' "
            "- field attribute is not defined"
        )
        mock_logger.debug.assert_any_call(target)
        self.assertEqual(1, mock_field_save.call_count)

    @patch("import_export.resources.logger")
    @patch("import_export.fields.Field.save")
    @ignore_widget_deprecation_warning
    def test_import_with_missing_field_in_row(self, mock_field_save, mock_logger):
        dataset = tablib.Dataset(*[(1, "Some book")], headers=["id", "name"])
        self.resource = BookResource()
        result = self.resource.import_data(dataset)
        self.assertFalse(result.has_errors())
        mock_logger.debug.assert_any_call(
            "skipping field '<import_export.fields.Field: author_email>' "
            "- column name 'author_email' is not present in row"
        )
        self.assertEqual(2, mock_field_save.call_count)
