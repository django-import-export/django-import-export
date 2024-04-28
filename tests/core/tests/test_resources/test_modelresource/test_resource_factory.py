from core.models import Book
from django.test import TestCase

from import_export import resources


class ModelResourceFactoryTest(TestCase):
    def test_create(self):
        BookResource = resources.modelresource_factory(Book)
        self.assertIn("id", BookResource.fields)
        self.assertEqual(BookResource._meta.model, Book)
