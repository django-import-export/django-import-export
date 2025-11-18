import warnings

import tablib
from core.models import Book
from django.db.models.functions import JSONObject
from django.test import TestCase

import import_export
import import_export.exceptions
from import_export import fields, resources

# ignore warnings which result from invalid field declaration (#1930)
warnings.simplefilter("ignore")


class ModelResourceFieldDeclarations(TestCase):
    class MyBookResource(resources.ModelResource):
        author_email = fields.Field(
            attribute="author_email", column_name="author_email"
        )

        class Meta:
            model = Book
            fields = ("id", "price")

    def setUp(self):
        self.book = Book.objects.create(name="Moonraker", price=".99")
        self.resource = ModelResourceFieldDeclarations.MyBookResource()

    def test_declared_field_not_imported(self):
        self.assertEqual("", self.book.author_email)
        rows = [
            (self.book.id, "12.99", "jj@example.com"),
        ]
        dataset = tablib.Dataset(*rows, headers=["id", "price", "author_email"])
        self.resource.import_data(dataset, raise_errors=True)
        self.book.refresh_from_db()
        # email should not be updated
        self.assertEqual("", self.book.author_email)

    def test_declared_field_not_exported(self):
        self.assertEqual("", self.book.author_email)
        data = self.resource.export()
        self.assertFalse("author_email" in data.dict[0])


class ModelResourceNoFieldDeclarations(TestCase):
    # No `fields` declaration so all fields should be included
    class MyBookResource(resources.ModelResource):
        author_email = fields.Field(
            attribute="author_email", column_name="author_email"
        )

        class Meta:
            model = Book

    def setUp(self):
        self.book = Book.objects.create(name="Moonraker", price=".99")
        self.resource = ModelResourceNoFieldDeclarations.MyBookResource()

    def test_declared_field_imported(self):
        self.assertEqual("", self.book.author_email)
        rows = [
            (self.book.id, "12.99", "jj@example.com"),
        ]
        dataset = tablib.Dataset(*rows, headers=["id", "price", "author_email"])
        self.resource.import_data(dataset, raise_errors=True)
        self.book.refresh_from_db()
        # email should be updated
        self.assertEqual("jj@example.com", self.book.author_email)

    def test_declared_field_not_exported(self):
        self.assertEqual("", self.book.author_email)
        data = self.resource.export()
        self.assertTrue("author_email" in data.dict[0])


class ModelResourceExcludeDeclarations(TestCase):
    class MyBookResource(resources.ModelResource):
        author_email = fields.Field(
            attribute="author_email", column_name="author_email"
        )

        class Meta:
            model = Book
            fields = ("id", "price")
            exclude = ("author_email",)

    def setUp(self):
        self.book = Book.objects.create(name="Moonraker", price=".99")
        self.resource = ModelResourceExcludeDeclarations.MyBookResource()

    def test_excluded_field_not_imported(self):
        self.assertEqual("", self.book.author_email)
        rows = [
            (self.book.id, "12.99", "jj@example.com"),
        ]
        dataset = tablib.Dataset(*rows, headers=["id", "price", "author_email"])
        self.resource.import_data(dataset, raise_errors=True)
        self.book.refresh_from_db()
        # email should not be updated
        self.assertEqual("", self.book.author_email)

    def test_declared_field_not_exported(self):
        self.assertEqual("", self.book.author_email)
        data = self.resource.export()
        self.assertFalse("author_email" in data.dict[0])


class ModelResourceFieldsAndExcludeDeclarations(TestCase):
    # Include the same field in both `fields` and `exclude`.
    # `fields` should take precedence.
    class MyBookResource(resources.ModelResource):
        author_email = fields.Field(
            attribute="author_email", column_name="author_email"
        )

        class Meta:
            model = Book
            fields = ("id", "price", "author_email")
            exclude = ("author_email",)

    def setUp(self):
        self.book = Book.objects.create(name="Moonraker", price=".99")
        self.resource = ModelResourceFieldsAndExcludeDeclarations.MyBookResource()

    def test_excluded_field_not_imported(self):
        self.assertEqual("", self.book.author_email)
        rows = [
            (self.book.id, "12.99", "jj@example.com"),
        ]
        dataset = tablib.Dataset(*rows, headers=["id", "price", "author_email"])
        self.resource.import_data(dataset, raise_errors=True)
        self.book.refresh_from_db()
        # email should be updated
        self.assertEqual("jj@example.com", self.book.author_email)

    def test_declared_field_not_exported(self):
        self.assertEqual("", self.book.author_email)
        data = self.resource.export()
        self.assertTrue("author_email" in data.dict[0])


class ModelResourceDeclarationsNotInImportTest(TestCase):
    # issue 1697
    # Add a declared field to the Resource, which is not present in the import file.
    # The import should succeed without issue.
    class MyBookResource(resources.ModelResource):
        author_email = fields.Field(
            attribute="author_email", column_name="author_email"
        )

        class Meta:
            model = Book
            fields = (
                "id",
                "price",
            )

    def setUp(self):
        self.resource = ModelResourceDeclarationsNotInImportTest.MyBookResource()

    def test_excluded_field_not_imported(self):
        rows = [
            ("1", "12.99"),
        ]
        dataset = tablib.Dataset(*rows, headers=["id", "price"])
        result = self.resource.import_data(dataset, raise_errors=True)
        book = Book.objects.first()
        self.assertEqual("", book.author_email)
        self.assertEqual(1, result.totals["new"])

    def test_excluded_field_not_exported(self):
        self.book = Book.objects.create(name="Moonraker", price=".99")
        self.assertEqual("", self.book.author_email)
        data = self.resource.export()
        self.assertFalse("author_email" in data.dict[0])


class ModelResourceUnusedFieldWarnings(TestCase):
    """
    Model Resources should warn on ignored declared fields, but only if
    they are declared on the current class.

    Ref: #2017
    """

    class _BaseBookResource(resources.ModelResource):
        name = fields.Field(
            attribute="name",
        )
        imported = fields.Field(
            attribute="imported",
        )
        price = fields.Field(
            attribute="price",
        )

        class Meta:
            model = Book
            fields = (
                "name",
                "imported",
                "price",
            )

    def setUp(self):
        # Enable warnings for this test
        warnings.simplefilter("default")

    def test_no_warnings_defined_fields(self):
        """
        A subclass that lists a subset of the parents defined fields
        should receive no warnings.
        """
        with warnings.catch_warnings(record=True) as w:

            class _Export1BookResource(self._BaseBookResource):
                class Meta:
                    fields = (
                        "name",
                        "imported",
                    )

            # expect no warnings
            self.assertEqual(len(w), 0)

    def test_declared_field_expect_warning(self):
        """
        A class that defines a field, but doesn't list it in fields
        should receive a warning with the name of the field and the
        class name
        """
        with warnings.catch_warnings(record=True) as w:

            class _Export2BookResource(self._BaseBookResource):
                published = fields.Field(attribute="published")
                published_time = fields.Field(attribute="published_time")

                class Meta:
                    fields = ("author_email", "imported", "published_time")

            self.assertEqual(len(w), 1)
            self.assertIs(w[0].category, UserWarning)
            self.assertIn(
                "_Export2BookResource: ignoring field 'published' because not"
                " declared in 'fields' whitelist",
                str(w[0].message),
            )


class ModelResourceDeclarationFieldWithDictKey(TestCase):

    class BookResource(resources.ModelResource):
        author_name = fields.Field(
            attribute="author_json__name", column_name="author_name", readonly=True
        )

        class Meta:
            model = Book
            fields = ("id", "author_name")

        def get_queryset(self):
            return (
                super()
                .get_queryset()
                .annotate(author_json=JSONObject(name=("author__name")))
            )

    def setUp(self):
        self.book = Book.objects.create(name="Moonraker", price=".99")
        self.resource = ModelResourceDeclarationFieldWithDictKey.BookResource()

    def test_declared_field_not_readonly_and_raises_error(self):
        """
        Test that when the fields with dict keys are declared and is not declared
        as readonly,it can`t be imported and raises an error.
        """
        self.resource.fields["author_name"].readonly = False
        rows = [
            (self.book.id, "New Author"),
        ]
        dataset = tablib.Dataset(*rows, headers=["id", "author_name"])
        with self.assertRaises(import_export.exceptions.ImportError) as context:
            self.resource.import_data(dataset, raise_errors=True)
        assert "1: 'dict' object has no attribute 'name' and no __dict__ for "
        "setting new attributes (OrderedDict({'id': 1, "
        "'author_name': 'New Author'}))" == str(context.exception)

    def test_declared_field_readonly_and_imported(self):
        """
        Test that when the fields with dict keys are declared as readonly,
        it can be imported without raising an error.
        For this resources this not will have any effect, but at least
        it will not raise an error.
        """
        rows = [
            (self.book.id, "New Author"),
        ]
        dataset = tablib.Dataset(*rows, headers=["id", "author_name"])
        self.resource.import_data(dataset, raise_errors=True)
