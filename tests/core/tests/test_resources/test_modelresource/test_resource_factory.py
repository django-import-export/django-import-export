from core.models import Book
from django.test import TestCase

from import_export import resources


class ModelResourceFactoryTest(TestCase):
    def test_create(self):
        BookResource = resources.modelresource_factory(Book)
        self.assertIn("id", BookResource.fields)
        self.assertEqual(BookResource._meta.model, Book)

    def test_create_with_meta_options(self):
        BookResource = resources.modelresource_factory(
            Book,
            meta_options={
                "fields": ("id", "name"),
                "exclude": ("imported",),
                "use_bulk": True,
                "clean_model_instances": True,
            },
        )

        self.assertEqual(BookResource._meta.fields, ("id", "name"))
        self.assertEqual(BookResource._meta.exclude, ("imported",))
        self.assertTrue(BookResource._meta.use_bulk)
        self.assertTrue(BookResource._meta.clean_model_instances)

    def test_resource_class_inheritance(self):
        class CustomModelResource(resources.ModelResource):
            def custom_method(self):
                return "custom"

        BookResource = resources.modelresource_factory(
            Book,
            resource_class=CustomModelResource,
        )

        resource = BookResource()

        self.assertTrue(hasattr(resource, "custom_method"))
        self.assertEqual(resource.custom_method(), "custom")

    def test_widgets_in_meta_options(self):
        BookResource = resources.modelresource_factory(
            Book,
            meta_options={
                "fields": ("id", "name", "price"),
                "widgets": {
                    "price": {"coerce_to_string": True},
                    "name": {"coerce_to_string": True},
                },
            },
        )

        # Check that meta options were set correctly
        self.assertEqual(BookResource._meta.fields, ("id", "name", "price"))
        self.assertIn("price", BookResource._meta.widgets)
        self.assertIn("name", BookResource._meta.widgets)

    def test_complex_meta_options(self):
        """Test complex meta options configuration"""
        BookResource = resources.modelresource_factory(
            Book,
            meta_options={
                "fields": ("id", "name", "author", "price"),
                "exclude": ("imported",),
                "import_id_fields": ("name",),
                "export_order": ("name", "author", "price", "id"),
                "use_bulk": True,
                "batch_size": 500,
                "skip_unchanged": True,
                "clean_model_instances": True,
                "widgets": {"price": {"coerce_to_string": True}},
            },
        )

        resource = BookResource()

        # Verify all meta options
        self.assertEqual(resource._meta.fields, ("id", "name", "author", "price"))
        self.assertEqual(resource._meta.exclude, ("imported",))
        self.assertEqual(resource._meta.import_id_fields, ("name",))
        self.assertEqual(resource._meta.export_order, ("name", "author", "price", "id"))
        self.assertTrue(resource._meta.use_bulk)
        self.assertEqual(resource._meta.batch_size, 500)
        self.assertTrue(resource._meta.skip_unchanged)
        self.assertTrue(resource._meta.clean_model_instances)
        self.assertIn("price", resource._meta.widgets)
