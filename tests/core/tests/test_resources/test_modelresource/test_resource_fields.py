import warnings

import tablib
from core.models import Book
from django.test import TestCase

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
