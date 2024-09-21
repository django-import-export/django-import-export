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
