from core.models import Book
from django.test import TestCase

from import_export import resources


class ModelResourceFactoryTest(TestCase):
    def test_create(self):
        BookResource = resources.modelresource_factory(Book)
        self.assertIn("id", BookResource.fields)
        self.assertEqual(BookResource._meta.model, Book)

    def test_create_with_meta(self):
        BookResource = resources.modelresource_factory(
            Book, meta_options={"clean_model_instances": True}
        )
        self.assertEqual(BookResource._meta.clean_model_instances, True)
