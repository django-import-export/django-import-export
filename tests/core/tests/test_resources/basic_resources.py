from collections import OrderedDict
from unittest import mock
from unittest.mock import patch

import tablib
from django.test import TestCase

from import_export import fields, resources, results
from tests.core.models import Author, Book, Category, Profile, WithDefault


class MyResource(resources.Resource):
    name = fields.Field()
    email = fields.Field()
    extra = fields.Field()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.kwargs = kwargs

    class Meta:
        export_order = ("email", "name")


class ResourceTestCase(TestCase):
    def setUp(self):
        self.my_resource = MyResource()

    def test_fields(self):
        """Check that fields were determined correctly"""

        # check that our fields were determined
        self.assertIn("name", self.my_resource.fields)

        # check that resource instance fields attr isn't link to resource cls
        # fields
        self.assertFalse(MyResource.fields is self.my_resource.fields)

        # dynamically add new resource field into resource instance
        self.my_resource.fields.update(
            OrderedDict(
                [
                    ("new_field", fields.Field()),
                ]
            )
        )

        # check that new field in resource instance fields
        self.assertIn("new_field", self.my_resource.fields)

        # check that new field not in resource cls fields
        self.assertNotIn("new_field", MyResource.fields)

    def test_kwargs(self):
        target_kwargs = {"a": 1}
        my_resource = MyResource(**target_kwargs)
        self.assertEqual(my_resource.kwargs, target_kwargs)

    def test_field_column_name(self):
        field = self.my_resource.fields["name"]
        self.assertIn(field.column_name, "name")

    def test_meta(self):
        self.assertIsInstance(self.my_resource._meta, resources.ResourceOptions)

    @mock.patch("builtins.dir")
    def test_new_handles_null_options(self, mock_dir):
        # #1163 - simulates a call to dir() returning additional attributes
        mock_dir.return_value = ["attrs"]

        class A(MyResource):
            pass

        A()

    def test_get_export_headers_order(self):
        self.assertEqual(
            self.my_resource.get_export_headers(), ["email", "name", "extra"]
        )

    def test_default_after_import(self):
        self.assertIsNone(
            self.my_resource.after_import(
                tablib.Dataset(),
                results.Result(),
            )
        )

    # Issue 140 Attributes aren't inherited by subclasses
    def test_inheritance(self):
        class A(MyResource):
            inherited = fields.Field()

            class Meta:
                import_id_fields = ("email",)

        class B(A):
            local = fields.Field()

            class Meta:
                export_order = ("email", "extra")

        resource = B()
        self.assertIn("name", resource.fields)
        self.assertIn("inherited", resource.fields)
        self.assertIn("local", resource.fields)
        self.assertEqual(
            resource.get_export_headers(),
            ["email", "extra", "name", "inherited", "local"],
        )
        self.assertEqual(resource._meta.import_id_fields, ("email",))

    def test_inheritance_with_custom_attributes(self):
        class A(MyResource):
            inherited = fields.Field()

            class Meta:
                import_id_fields = ("email",)
                custom_attribute = True

        class B(A):
            local = fields.Field()

        resource = B()
        self.assertEqual(resource._meta.custom_attribute, True)

    def test_get_use_transactions_defined_in_resource(self):
        class A(MyResource):
            class Meta:
                use_transactions = True

        resource = A()
        self.assertTrue(resource.get_use_transactions())

    def test_get_field_name_raises_AttributeError(self):
        err = (
            "Field x does not exists in <class "
            "'core.tests.test_resources.MyResource'> resource"
        )
        with self.assertRaisesRegex(AttributeError, err):
            self.my_resource.get_field_name("x")

    def test_init_instance_raises_NotImplementedError(self):
        with self.assertRaises(NotImplementedError):
            self.my_resource.init_instance([])

    @patch("core.models.Book.full_clean")
    def test_validate_instance_called_with_import_validation_errors_as_None(
        self, full_clean_mock
    ):
        # validate_instance() import_validation_errors is an optional kwarg
        # If not provided, it defaults to an empty dict
        # this tests that scenario by ensuring that an empty dict is passed
        # to the model instance full_clean() method.
        book = Book()
        self.my_resource._meta.clean_model_instances = True
        self.my_resource.validate_instance(book)
        target = dict()
        full_clean_mock.assert_called_once_with(
            exclude=target.keys(), validate_unique=True
        )


class AuthorResource(resources.ModelResource):
    books = fields.Field(
        column_name="books",
        attribute="book_set",
        readonly=True,
    )

    class Meta:
        model = Author
        export_order = ("name", "books")


class BookResource(resources.ModelResource):
    published = fields.Field(column_name="published_date")

    class Meta:
        model = Book
        exclude = ("imported",)


class CategoryResource(resources.ModelResource):
    class Meta:
        model = Category


class ProfileResource(resources.ModelResource):
    class Meta:
        model = Profile
        exclude = ("user",)


class WithDefaultResource(resources.ModelResource):
    class Meta:
        model = WithDefault
        fields = ("name",)
