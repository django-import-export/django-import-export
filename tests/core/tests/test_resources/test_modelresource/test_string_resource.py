from core.models import Book
from django.test import TestCase

from import_export import resources


class BookResourceWithStringModelTest(TestCase):
    def setUp(self):
        class BookResourceWithStringModel(resources.ModelResource):
            class Meta:
                model = "core.Book"

        self.resource = BookResourceWithStringModel()

    def test_resource_gets_correct_model_from_string(self):
        self.assertEqual(self.resource._meta.model, Book)
