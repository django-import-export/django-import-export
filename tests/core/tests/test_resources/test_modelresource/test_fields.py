from unittest import mock

import tablib
from core.models import Book
from core.tests.resources import BookResource
from django.test import TestCase

from import_export import fields, resources, widgets


class FieldHandlingTest(TestCase):
    def setUp(self):
        self.resource = BookResource()
        self.book = Book.objects.create(name="Some book")
        self.dataset = tablib.Dataset(headers=["id", "name", "author_email", "price"])
        row = [self.book.pk, "Some book", "test@example.com", "10.25"]
        self.dataset.append(row)

    def test_get_instance(self):
        instance_loader = self.resource._meta.instance_loader_class(self.resource)
        self.resource._meta.import_id_fields = ["id"]
        instance = self.resource.get_instance(instance_loader, self.dataset.dict[0])
        self.assertEqual(instance, self.book)

    def test_get_instance_import_id_fields(self):
        class BookResource(resources.ModelResource):
            name = fields.Field(attribute="name", widget=widgets.CharWidget())

            class Meta:
                model = Book
                import_id_fields = ["name"]

        resource = BookResource()
        instance_loader = resource._meta.instance_loader_class(resource)
        instance = resource.get_instance(instance_loader, self.dataset.dict[0])
        self.assertEqual(instance, self.book)

    def test_get_instance_usually_defers_to_instance_loader(self):
        self.resource._meta.import_id_fields = ["id"]

        instance_loader = self.resource._meta.instance_loader_class(self.resource)

        with mock.patch.object(instance_loader, "get_instance") as mocked_method:
            row = self.dataset.dict[0]
            self.resource.get_instance(instance_loader, row)
            # instance_loader.get_instance() should have been called
            mocked_method.assert_called_once_with(row)
