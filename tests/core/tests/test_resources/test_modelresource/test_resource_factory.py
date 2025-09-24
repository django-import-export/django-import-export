from core.models import Author, Book
from django.test import TestCase

from import_export import fields, resources, widgets


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

    def test_custom_fields(self):
        custom_field = fields.Field(column_name="Custom Title", readonly=True)

        BookResource = resources.modelresource_factory(
            Book, custom_fields={"custom_title": custom_field}
        )

        self.assertIn("custom_title", BookResource.fields)
        self.assertEqual(BookResource.fields["custom_title"], custom_field)
        self.assertEqual(
            BookResource.fields["custom_title"].column_name, "Custom Title"
        )
        self.assertTrue(BookResource.fields["custom_title"].readonly)

    def test_custom_fields_validation(self):
        with self.assertRaises(ValueError) as cm:
            resources.modelresource_factory(
                Book, custom_fields={"invalid_field": "not a field object"}
            )

        self.assertIn("must be a Field instance", str(cm.exception))
        self.assertIn("custom_fields['invalid_field']", str(cm.exception))

    def test_dehydrate_methods(self):
        def custom_dehydrate_custom_title(obj):
            return f"{obj.name} - Custom"

        BookResource = resources.modelresource_factory(
            Book,
            custom_fields={"custom_title": fields.Field(column_name="Custom Title")},
            dehydrate_methods={"custom_title": custom_dehydrate_custom_title},
        )

        self.assertTrue(hasattr(BookResource, "dehydrate_custom_title"))

        resource = BookResource()
        book = Book.objects.create(name="Test Book")
        result = resource.dehydrate_custom_title(book)
        self.assertEqual(result, "Test Book - Custom")

    def test_dehydrate_methods_validation(self):
        with self.assertRaises(ValueError) as cm:
            resources.modelresource_factory(
                Book, dehydrate_methods={"field_name": "not callable"}
            )

        self.assertIn("must be callable", str(cm.exception))
        self.assertIn("dehydrate_methods['field_name']", str(cm.exception))

    def test_lambda_dehydrate_methods(self):
        BookResource = resources.modelresource_factory(
            Book,
            custom_fields={"custom_title": fields.Field(column_name="Custom Title")},
            dehydrate_methods={
                "custom_title": (
                    lambda obj: (
                        f"{obj.name} by {getattr(obj.author, 'name', 'Unknown')}"
                    )
                )
            },
        )

        author = Author.objects.create(name="Test Author")
        book = Book.objects.create(name="Test Book", author=author)

        resource = BookResource()
        result = resource.dehydrate_custom_title(book)
        self.assertEqual(result, "Test Book by Test Author")

        book_no_author = Book.objects.create(name="Book")
        result = resource.dehydrate_custom_title(book_no_author)
        self.assertEqual(result, "Book by Unknown")

    def test_comprehensive_example(self):
        """Test a comprehensive example with multiple features"""
        BookResource = resources.modelresource_factory(
            Book,
            meta_options={
                "fields": ("id", "name", "author", "custom_title", "status"),
                "import_id_fields": ("name",),
                "use_bulk": True,
            },
            custom_fields={
                "custom_title": fields.Field(column_name="Custom Title", readonly=True),
                "status": fields.Field(
                    attribute="imported",
                    column_name="Import Status",
                    widget=widgets.BooleanWidget(),
                ),
            },
            dehydrate_methods={"custom_title": lambda obj: f"{obj.name} - {obj.pk}"},
        )

        resource = BookResource()

        self.assertEqual(
            resource._meta.fields, ("id", "name", "author", "custom_title", "status")
        )
        self.assertEqual(resource._meta.import_id_fields, ("name",))
        self.assertTrue(resource._meta.use_bulk)

        self.assertIn("custom_title", resource.fields)
        self.assertIn("status", resource.fields)
        self.assertTrue(resource.fields["custom_title"].readonly)

        self.assertTrue(hasattr(resource, "dehydrate_custom_title"))

        book = Book.objects.create(name="Test Book")
        custom_title_result = resource.dehydrate_custom_title(book)
        self.assertEqual(custom_title_result, f"Test Book - {book.pk}")

        dataset = resource.export([book])
        self.assertEqual(len(dataset), 1)

    def test_field_with_dehydrate_method_attribute(self):
        BookResource1 = resources.modelresource_factory(
            Book,
            custom_fields={
                "custom_title": fields.Field(
                    column_name="Custom Title",
                    dehydrate_method=lambda obj: f"Field method: {obj.name}",
                )
            },
        )

        BookResource2 = resources.modelresource_factory(
            Book,
            custom_fields={"custom_title": fields.Field(column_name="Custom Title")},
            dehydrate_methods={
                "custom_title": lambda obj: f"Factory method: {obj.name}"
            },
        )

        book = Book.objects.create(name="Test Book")

        resource1 = BookResource1()
        field1 = resource1.fields["custom_title"]
        self.assertTrue(callable(field1.dehydrate_method))

        resource2 = BookResource2()
        self.assertTrue(hasattr(resource2, "dehydrate_custom_title"))
        result2 = resource2.dehydrate_custom_title(book)
        self.assertEqual(result2, "Factory method: Test Book")

    def test_empty_parameters(self):
        BookResource = resources.modelresource_factory(
            Book,
            custom_fields={},
            dehydrate_methods={},
        )

        self.assertIn("id", BookResource.fields)
        self.assertEqual(BookResource._meta.model, Book)

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
