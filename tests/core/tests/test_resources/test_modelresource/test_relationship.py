from datetime import date

import tablib
from core.models import Author, Book
from core.tests.resources import BookResource
from django.test import TestCase

from import_export import fields, resources


class RelationshipFieldTest(TestCase):
    def setUp(self):
        self.resource = BookResource()
        self.book = Book.objects.create(name="Some book")
        self.dataset = tablib.Dataset(headers=["id", "name", "author_email", "price"])
        row = [self.book.pk, "Some book", "test@example.com", "10.25"]
        self.dataset.append(row)

    def test_relationships_fields(self):
        class B(resources.ModelResource):
            class Meta:
                model = Book
                fields = ("author__name",)

        author = Author.objects.create(name="Author")
        self.book.author = author
        resource = B()
        result = resource.fields["author__name"].export(self.book)
        self.assertEqual(result, author.name)

    def test_dehydrating_fields(self):
        class B(resources.ModelResource):
            full_title = fields.Field(column_name="Full title")

            class Meta:
                model = Book
                fields = ("author__name", "full_title")

            def dehydrate_full_title(self, obj):
                return f"{obj.name} by {obj.author.name}"

        author = Author.objects.create(name="Author")
        self.book.author = author
        resource = B()
        full_title = resource.export_field(resource.fields["full_title"], self.book)
        self.assertEqual(full_title, f"{self.book.name} by {self.book.author.name}")

    def test_dehydrating_field_using_callable(self):
        class B(resources.ModelResource):
            full_title = fields.Field(
                column_name="Full title",
                dehydrate_method=lambda obj: f"{obj.name} by {obj.author.name}",
            )

            class Meta:
                model = Book
                fields = ("author__name", "full_title")

        author = Author.objects.create(name="Author")
        self.book.author = author
        resource = B()
        full_title = resource.export_field(resource.fields["full_title"], self.book)
        self.assertEqual(full_title, f"{self.book.name} by {self.book.author.name}")

    def test_dehydrate_field_using_custom_dehydrate_field_method(self):
        class B(resources.ModelResource):
            full_title = fields.Field(
                column_name="Full title", dehydrate_method="foo_dehydrate_full_title"
            )

            class Meta:
                model = Book
                fields = "full_title"

            def foo_dehydrate_full_title(self, obj):
                return f"{obj.name} by {obj.author.name}"

        author = Author.objects.create(name="Author")
        self.book.author = author
        resource = B()

        full_title = resource.export_field(resource.fields["full_title"], self.book)
        self.assertEqual(full_title, f"{self.book.name} by {self.book.author.name}")

    def test_invalid_relation_field_name(self):
        class B(resources.ModelResource):
            full_title = fields.Field(column_name="Full title")

            class Meta:
                model = Book
                # author_name is not a valid field or relation,
                # so should be ignored
                fields = ("author_name", "full_title")

        resource = B()
        self.assertEqual(1, len(resource.fields))
        self.assertEqual("full_title", list(resource.fields.keys())[0])

    def test_widget_format_in_fk_field(self):
        class B(resources.ModelResource):
            class Meta:
                model = Book
                fields = ("author__birthday",)
                widgets = {
                    "author__birthday": {"format": "%Y-%m-%d"},
                }

        author = Author.objects.create(name="Author")
        self.book.author = author
        resource = B()
        result = resource.fields["author__birthday"].export(self.book)
        self.assertEqual(result, str(date.today()))

    def test_widget_kwargs_for_field(self):
        class B(resources.ModelResource):
            class Meta:
                model = Book
                fields = ("published",)
                widgets = {
                    "published": {"format": "%d.%m.%Y"},
                }

        resource = B()
        self.book.published = date(2012, 8, 13)
        result = resource.fields["published"].export(self.book)
        self.assertEqual(result, "13.08.2012")


class ForeignKeyWidgetImportExportTest(TestCase):
    """
    Issue #2107:
    ForeignKey widget field configuration must not be
    ignored during import & export.
    """

    def setUp(self):
        self.author = Author.objects.create(name="Test Author")
        self.book = Book.objects.create(name="Test Book", author=self.author)

    def test_foreign_key_widget_field_import(self):
        """
        Test that proves ForeignKeyWidget field configuration works for import.
        This test imports data with author names (not IDs) and verifies that the widget
        correctly resolves the names to Author objects during import.
        This demonstrates that import works in v4, proving export is a regression.
        """
        # Create additional test authors for import
        author2 = Author.objects.create(name="Second Author")
        author3 = Author.objects.create(name="Third Author")

        class BookResourceWithAuthorNameWidget(resources.ModelResource):
            class Meta:
                model = Book
                fields = ("id", "name", "author")
                widgets = {
                    "author": {"field": "name"},
                }

        # Create dataset with author names instead of IDs
        dataset = tablib.Dataset(headers=["name", "author"])
        dataset.append(["Book One", "Test Author"])  # Uses existing author from setUp
        dataset.append(["Book Two", "Second Author"])
        dataset.append(["Book Three", "Third Author"])

        resource = BookResourceWithAuthorNameWidget()

        # Count books before import
        initial_book_count = Book.objects.count()

        # Import the data
        result = resource.import_data(dataset, raise_errors=True)

        # Verify import was successful
        self.assertFalse(result.has_errors())
        self.assertEqual(len(result.rows), 3)

        # Verify new books were created
        self.assertEqual(Book.objects.count(), initial_book_count + 3)

        # Verify books have correct author relationships
        book_one = Book.objects.get(name="Book One")
        self.assertEqual(book_one.author, self.author)  # Test Author from setUp

        book_two = Book.objects.get(name="Book Two")
        self.assertEqual(book_two.author, author2)

        book_three = Book.objects.get(name="Book Three")
        self.assertEqual(book_three.author, author3)

    def test_foreign_key_widget_field_export(self):
        """
        Test that demonstrates the bug where ForeignKeyWidget field configuration
        is ignored during export. The widget should export the author name instead
        of the ID, but currently exports the ID.
        """

        class BookResourceWithAuthorNameWidget(resources.ModelResource):
            class Meta:
                model = Book
                fields = ("name", "author")
                widgets = {
                    "author": {"field": "name"},
                }

        resource = BookResourceWithAuthorNameWidget()
        dataset = resource.export(queryset=Book.objects.filter(id=self.book.id))

        # Get the exported value for comparison
        exported_author_value = dataset.dict[0]["author"]

        self.assertEqual(
            exported_author_value,
            "Test Author",
            f"Expected author name 'Test Author' but got '{exported_author_value}'",
        )
