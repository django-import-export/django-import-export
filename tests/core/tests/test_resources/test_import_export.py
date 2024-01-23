from datetime import date
from unittest.mock import patch

import tablib
from core.models import Author, Book, Category
from core.tests.resources import BookResource
from core.tests.utils import ignore_widget_deprecation_warning
from django.test import TestCase

from import_export import exceptions, fields, resources, widgets


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

    class DeclaredModelFieldBookResource(BaseBookResource):
        # Non-model field, should come after model fields by default
        author_full_name = fields.Field(
            attribute="author",
            column_name="author full name",
        )

        # Order of declared fields in `ModelResource` shouldn't change export order
        categories = fields.Field(
            attribute="categories",
            column_name="categories",
            widget=widgets.ManyToManyWidget(model=Category, field="name"),
        )
        published = fields.Field(
            attribute="published",
            column_name="published",
            widget=widgets.DateWidget("%d.%m.%Y"),
        )
        author = fields.Field(attribute="author__name", column_name="author")

        class Meta:
            model = Book

        def dehydrate_author_full_name(self, obj):
            if obj.author:
                return f"{obj.author.name} Bar"

            return ""

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

    def test_declared_model_fields_not_alter_export_order(self):
        # Issue (#1663)

        categories = [
            Category.objects.create(name="sci-fi"),
            Category.objects.create(name="romance"),
        ]
        author = Author.objects.create(name="Foo")
        book = Book.objects.create(
            name="The Lord Of The Rings", author=author, published=date(2022, 2, 2)
        )
        book.categories.set(categories)

        self.resource = ImportExportFieldOrderTest.DeclaredModelFieldBookResource()
        declared_field_names = (
            "published",
            "author",  # FK
            "categories",  # M2M
        )
        export_order = self.resource.get_export_order()
        model_fields_names = [
            field.name for field in self.resource._meta.model._meta.get_fields()
        ]

        for declared_field_name in declared_field_names:
            self.assertEqual(
                model_fields_names.index(declared_field_name),
                export_order.index(declared_field_name),
            )

        # Validate non-model field is exported last unless specified
        self.assertEqual(export_order[-1], "author_full_name")

    def test_meta_fields_not_alter_export_order(self):
        class DeclaredModelFieldBookResource(
            ImportExportFieldOrderTest.BaseBookResource
        ):
            # Non-model field, should come after model fields by default
            author_full_name = fields.Field(
                attribute="author",
                column_name="author full name",
            )

            # Order of declared fields in `ModelResource` shouldn't change export order
            categories = fields.Field(
                attribute="categories",
                column_name="categories",
                widget=widgets.ManyToManyWidget(model=Category, field="name"),
            )
            published = fields.Field(
                attribute="published",
                column_name="published",
                widget=widgets.DateWidget("%d.%m.%Y"),
            )
            author = fields.Field(attribute="author__name", column_name="author")

            class Meta:
                model = Book
                fields = (
                    "id",
                    "author__name",
                    "author",
                    "author_full_name",
                    "categories",
                    "published",
                )

            def dehydrate_author_full_name(self, obj):
                if obj.author:
                    return f"{obj.author.name} Bar"

                return ""

        self.resource = DeclaredModelFieldBookResource()
        self.assertEqual(self.resource.get_export_order(), self.resource._meta.fields)


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
        with self.assertRaises(exceptions.FieldError) as e:
            self.resource.import_data(dataset)
        self.assertEqual(
            "The following fields are declared in 'import_id_fields' "
            "but are not present in the resource: book_name",
            str(e.exception),
        )

    def test_missing_import_id_field_raises_exception(self):
        class TestBookResource(resources.ModelResource):
            class Meta:
                model = Book
                import_id_fields = ("id", "a", "b")

        resource = TestBookResource()

        book = Book.objects.create(name="Some book")
        row = [book.pk, "Some book"]
        dataset = tablib.Dataset(*[row], headers=["id", "name"])
        dataset.append(row)

        with self.assertRaises(exceptions.FieldError) as e:
            resource.import_data(dataset)
        self.assertEqual(
            "The following fields are declared in 'import_id_fields' "
            "but are not present in the resource: a, b",
            str(e.exception),
        )

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
        with self.assertRaises(exceptions.FieldError) as e:
            self.resource.import_data(dataset)
        self.assertEqual(
            "The following fields are declared in 'import_id_fields' "
            "but are not present in the resource: id, author_email",
            str(e.exception),
        )


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
