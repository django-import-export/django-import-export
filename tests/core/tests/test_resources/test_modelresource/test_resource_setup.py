import tablib
from core.models import Author, Book
from core.tests.resources import BookResource, WithDefaultResource
from django.test import TestCase

from import_export import resources, widgets
from import_export.instance_loaders import ModelInstanceLoader


class TestResourceSetup(TestCase):
    def setUp(self):
        self.resource = BookResource()
        self.book = Book.objects.create(name="Some book")
        self.dataset = tablib.Dataset(headers=["id", "name", "author_email", "price"])
        row = [self.book.pk, "Some book", "test@example.com", "10.25"]
        self.dataset.append(row)

    def test_default_instance_loader_class(self):
        self.assertIs(self.resource._meta.instance_loader_class, ModelInstanceLoader)

    def test_fields(self):
        fields = self.resource.fields
        self.assertIn("id", fields)
        self.assertIn("name", fields)
        self.assertIn("author_email", fields)
        self.assertIn("price", fields)

    def test_fields_foreign_key(self):
        fields = self.resource.fields
        self.assertIn("author", fields)
        widget = fields["author"].widget
        self.assertIsInstance(widget, widgets.ForeignKeyWidget)
        self.assertEqual(widget.model, Author)

    def test_get_display_name(self):
        display_name = self.resource.get_display_name()
        self.assertEqual(display_name, "BookResource")

        class BookResource(resources.ModelResource):
            class Meta:
                name = "Foo Name"
                model = Book
                import_id_fields = ["name"]

        resource = BookResource()
        display_name = resource.get_display_name()
        self.assertEqual(display_name, "Foo Name")

    def test_fields_m2m(self):
        fields = self.resource.fields
        self.assertIn("categories", fields)

    def test_excluded_fields(self):
        self.assertNotIn("imported", self.resource.fields)

    def test_init_instance(self):
        instance = self.resource.init_instance()
        self.assertIsInstance(instance, Book)

    def test_default(self):
        self.assertEqual(
            WithDefaultResource.fields["name"].clean({"name": ""}), "foo_bar"
        )
