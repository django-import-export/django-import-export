from datetime import date
from unittest.mock import patch

import tablib
from core.admin import UUIDBookResource
from core.models import Author, Book, Category, EBook, NamedAuthor, UUIDBook
from core.tests.resources import AuthorResource, BookResource
from django.test import TestCase

from import_export import exceptions, fields, resources, widgets
from import_export.fields import Field
from import_export.resources import ModelResource


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

    def test_after_import_row_check_for_change(self):
        # issue 1583 - assert that `original` object is available to after_import_row()
        self.resource.import_data(self.dataset, raise_errors=True)
        self.assertTrue(self.resource.is_published)


class ImportExportFieldOrderTest(TestCase):
    class BaseBookResource(resources.ModelResource):
        def __init__(self):
            self.field_names = []

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
            import_order = ["price", "name", "id"]
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

    class MixedIterableBookResource(BaseBookResource):
        class Meta:
            fields = ("price", "id", "name")
            import_order = ["price", "name", "id"]
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

    def test_mixed_iterable(self):
        # 1878
        self.resource = ImportExportFieldOrderTest.MixedIterableBookResource()
        self.resource.import_data(self.dataset)
        self.assertEqual(["price", "name", "id"], self.resource.field_names)

    def test_defined_import_order(self):
        self.resource = ImportExportFieldOrderTest.OrderedBookResource()
        self.resource.import_data(self.dataset)
        self.assertEqual(["price", "name", "id"], self.resource.field_names)

    def test_undefined_import_order(self):
        self.resource = ImportExportFieldOrderTest.UnorderedBookResource()
        self.resource.import_data(self.dataset)
        self.assertEqual(["price", "id", "name"], self.resource.field_names)

    def test_defined_export_order(self):
        self.resource = ImportExportFieldOrderTest.OrderedBookResource()
        data = self.resource.export()
        target = f"price,name,id\r\n1.99,Ulysses,{self.pk}\r\n"
        self.assertEqual(target, data.csv)

    def test_undefined_export_order(self):
        # When export order is not defined,
        # exported order should correspond with 'fields' definition
        self.resource = ImportExportFieldOrderTest.UnorderedBookResource()
        data = self.resource.export()
        target = f"price,id,name\r\n1.99,{self.pk},Ulysses\r\n"
        self.assertEqual(target, data.csv)

    def test_subset_import_order(self):
        self.resource = ImportExportFieldOrderTest.SubsetOrderedBookResource()
        self.resource.import_data(self.dataset)
        self.assertEqual(
            ["name", "price", "id", "published"], self.resource.field_names
        )

    def test_subset_export_order(self):
        self.resource = ImportExportFieldOrderTest.SubsetOrderedBookResource()
        data = self.resource.export()
        target = f"published,price,id,name\r\n,1.99,{self.pk},Ulysses\r\n"
        self.assertEqual(target, data.csv)

    def test_duplicate_import_order(self):
        self.resource = ImportExportFieldOrderTest.DuplicateFieldsBookResource()
        self.resource.import_data(self.dataset)
        self.assertEqual(["id", "price", "name"], self.resource.field_names)

    def test_duplicate_export_order(self):
        self.resource = ImportExportFieldOrderTest.DuplicateFieldsBookResource()
        data = self.resource.export()
        target = f"id,price,name\r\n{self.pk},1.99,Ulysses\r\n"
        self.assertEqual(target, data.csv)

    def test_fields_as_list_import_order(self):
        self.resource = ImportExportFieldOrderTest.FieldsAsListBookResource()
        self.resource.import_data(self.dataset)
        self.assertEqual(["id", "price", "name"], self.resource.field_names)

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

    def test_declared_field_export_order(self):
        # issue 1848
        class DeclaredModelFieldBookResource(
            ImportExportFieldOrderTest.BaseBookResource
        ):
            published = fields.Field(
                attribute="published",
                column_name="date published",
                widget=widgets.DateWidget("%d.%m.%Y"),
            )

            class Meta:
                model = Book
                fields = (
                    "id",
                    "author",
                    "published",
                )
                export_order = (
                    "published",
                    "id",
                    "author",
                )

        self.resource = DeclaredModelFieldBookResource()
        data = self.resource.export()
        target = f"date published,id,author\r\n,{self.pk},\r\n"
        self.assertEqual(target, data.csv)

    def test_export_fields_column_name(self):
        """Test export with declared export_fields and custom column_name"""

        # issue 1846
        class DeclaredModelFieldBookResource(resources.ModelResource):
            published = fields.Field(
                attribute="published",
                column_name="datePublished",
                widget=widgets.DateWidget("%d.%m.%Y"),
            )
            author = fields.Field(column_name="AuthorFooName")

            class Meta:
                model = Book
                fields = (
                    "id",
                    "author",
                    "published",
                )
                export_order = (
                    "published",
                    "id",
                    "author",
                )

            def dehydrate_author(self, obj):
                return obj.author

        self.resource = DeclaredModelFieldBookResource()
        data = self.resource.export()
        target = f"datePublished,id,AuthorFooName\r\n,{self.pk},\r\n"
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
        with self.assertRaises(exceptions.ImportError) as e:
            self.resource.import_data(dataset, raise_errors=True)
        self.assertEqual(
            "The following fields are declared in 'import_id_fields' "
            "but are not present in the file headers: book_name",
            str(e.exception),
        )

    def test_custom_column_name_warns_if_not_present_as_error_in_result(self):
        dataset = tablib.Dataset(
            *[(self.book.pk, "Some book")], headers=["id", "wrong_name"]
        )
        res = self.resource.import_data(dataset, raise_errors=False)
        target = (
            "The following fields are declared in 'import_id_fields' "
            "but are not present in the file headers: book_name"
        )
        self.assertEqual(target, str(res.base_errors[0].error))

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

        with self.assertRaises(exceptions.ImportError) as e:
            resource.import_data(dataset, raise_errors=True)
        self.assertEqual(
            "The following fields are declared in 'import_id_fields' "
            "but are not present in the resource fields: a, b",
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
        with self.assertRaises(exceptions.ImportError) as e:
            self.resource.import_data(dataset, raise_errors=True)
        self.assertEqual(
            "The following fields are declared in 'import_id_fields' "
            "but are not present in the file headers: id, author_email",
            str(e.exception),
        )

    def test_dynamic_import_id_fields(self):
        # issue 1834
        class BookResource(resources.ModelResource):
            def before_import(self, dataset, **kwargs):
                # mimic a 'dynamic field' - i.e. append field which exists on
                # Book model, but not in dataset
                dataset.headers.append("price")
                super().before_import(dataset, **kwargs)

            class Meta:
                model = Book
                import_id_fields = ("price",)

        self.resource = BookResource()
        dataset = tablib.Dataset(
            *[(self.book.pk, "Goldeneye", "ian.fleming@example.com")],
            headers=["id", "name", "author_email"],
        )
        self.resource.import_data(dataset, raise_errors=True)
        self.assertEqual("Goldeneye", Book.objects.latest("id").name)


class ImportWithMissingFields(TestCase):
    # issue 1517
    @patch("import_export.resources.logger")
    @patch("import_export.fields.Field.save")
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

    def test_import_row_with_no_defined_id_field(self):
        """Ensure a row with no id field can be imported (issue 1812)."""
        self.assertEqual(0, Author.objects.count())
        dataset = tablib.Dataset(*[("J. R. R. Tolkien",)], headers=["name"])
        self.resource = AuthorResource()
        self.resource.import_data(dataset)
        self.assertEqual(1, Author.objects.count())


class CustomColumnNameImportTest(TestCase):
    """
    If a custom field is declared, import should work if either the Field's
    attribute name or column name is referenced in the ``fields`` list (issue 1815).
    """

    fixtures = ["author"]

    class _EBookResource(ModelResource):
        published = Field(attribute="published", column_name="published_date")

        class Meta:
            model = EBook
            fields = ("id", "name", "published_date")

    def setUp(self):
        super().setUp()
        self.resource = CustomColumnNameImportTest._EBookResource()

    def test_import_with_column_alias_in_fields_list(self):
        self.assertEqual(0, EBook.objects.count())
        dataset = tablib.Dataset(
            *[(1, "Moonraker", "1955-04-05")], headers=["id", "name", "published_date"]
        )
        self.resource.import_data(dataset, raise_errors=True)
        self.assertEqual(1, EBook.objects.count())
        self.assertEqual(date(1955, 4, 5), EBook.objects.first().published)


class CustomPrimaryKeyRelationImportTest(TestCase):
    """
    Test issue 1852.
    Ensure import works when a relation has a custom primary key.
    """

    def setUp(self):
        super().setUp()
        # The name for this object is the PK
        self.named_author = NamedAuthor.objects.create(name="Ian Fleming")
        self.resource = UUIDBookResource()

    def test_custom_column_name_warns_if_not_present(self):
        dataset = tablib.Dataset(
            *[("Moonraker", "Ian Fleming")], headers=["name", "author"]
        )
        self.assertEqual(0, UUIDBook.objects.count())
        self.resource.import_data(dataset, raise_errors=True)
        self.assertEqual(1, UUIDBook.objects.count())


class DeclaredFieldWithNoAttributeTestCase(TestCase):
    """
    If a custom field is declared, import should skip setting an attribute if the
    Field declaration has no attribute name.
    # 1874
    """

    class _EBookResource(ModelResource):
        published = Field(column_name="published")

        class Meta:
            model = EBook
            fields = ("id", "name", "published")

    def setUp(self):
        super().setUp()
        self.resource = DeclaredFieldWithNoAttributeTestCase._EBookResource()

    @patch("import_export.resources.logger")
    def test_import_with_no_attribute(self, mock_logger):
        self.assertEqual(0, EBook.objects.count())
        dataset = tablib.Dataset(
            *[(1, "Moonraker", "1955-04-05")], headers=["id", "name", "published"]
        )
        self.resource.import_data(dataset, raise_errors=True)
        self.assertEqual(1, EBook.objects.count())
        self.assertIsNone(EBook.objects.first().published)
        mock_logger.debug.assert_any_call(
            "skipping field '<import_export.fields.Field: published>' "
            "- field attribute is not defined"
        )


class QuerysetValuesOnExportTest(TestCase):
    """
    Issue 2020 - export should handle QuerySet.values()
    """

    class _EBookResource(ModelResource):

        def get_queryset(self):
            return EBook.objects.all().values("id", "name", "published")

        class Meta:
            model = EBook
            fields = ("id", "name", "published")

    def setUp(self):
        super().setUp()
        self.resource = QuerysetValuesOnExportTest._EBookResource()
        EBook.objects.create(id=101, name="Moonraker", published=date(1955, 4, 5))

    def test_export(self):
        res = self.resource.export()
        self.assertEqual(1, len(res.dict))
        self.assertDictEqual(
            {"id": "101", "name": "Moonraker", "published": "1955-04-05"},
            res.dict.pop(),
        )

    def test_get_value_returns_none_when_attribute_missing(self):
        instance = {"some_other_key": "value"}
        field = Field(attribute="missing_attribute")

        result = field.get_value(instance)
        self.assertIsNone(result)
