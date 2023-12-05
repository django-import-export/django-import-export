from collections import OrderedDict
from unittest import mock
from unittest.mock import patch

import tablib
from django.test import TestCase

from import_export import fields, resources, results

from ...models import Book


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

    def test_get_export_order(self):
        self.assertEqual(
            self.my_resource.get_export_headers(), ["email", "name", "extra"]
        )

    def test_default_after_import(self):
        self.assertIsNone(
            self.my_resource.after_import(
                tablib.Dataset(), results.Result(), False, False
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

    def test_raise_errors_deprecation_import_row(
        self,
    ):
        target_msg = (
            "raise_errors argument is deprecated and "
            "will be removed in a future release."
        )
        dataset = tablib.Dataset(headers=["name", "email", "extra"])
        dataset.append(["Some book", "test@example.com", "10.25"])

        class Loader:
            def __init__(self, *args, **kwargs):
                pass

        class A(MyResource):
            class Meta:
                instance_loader_class = Loader
                force_init_instance = True

            def init_instance(self, row=None):
                return row or {}

            def import_row(
                self,
                row,
                instance_loader,
                using_transactions=True,
                dry_run=False,
                raise_errors=False,
                **kwargs,
            ):
                return super().import_row(
                    row,
                    instance_loader,
                    using_transactions,
                    dry_run,
                    raise_errors,
                    **kwargs,
                )

            def save_instance(
                self, instance, is_create, using_transactions=True, dry_run=False
            ):
                pass

        resource = A()
        with self.assertWarns(DeprecationWarning) as w:
            resource.import_data(dataset, raise_errors=True)
            self.assertEqual(target_msg, str(w.warnings[0].message))

    def test_rollback_on_validation_errors_deprecation_import_inner(
        self,
    ):
        target_msg = (
            "rollback_on_validation_errors argument is deprecated "
            "and will be removed in a future release."
        )
        dataset = tablib.Dataset(headers=["name", "email", "extra"])
        dataset.append(["Some book", "test@example.com", "10.25"])

        class Loader:
            def __init__(self, *args, **kwargs):
                pass

        class A(MyResource):
            class Meta:
                instance_loader_class = Loader
                force_init_instance = True

            def init_instance(self, row=None):
                return row or {}

            def import_data_inner(
                self,
                dataset,
                dry_run,
                raise_errors,
                using_transactions,
                collect_failed_rows,
                rollback_on_validation_errors=False,
                **kwargs,
            ):
                return super().import_data_inner(
                    dataset,
                    dry_run,
                    raise_errors,
                    using_transactions,
                    collect_failed_rows,
                    rollback_on_validation_errors,
                    **kwargs,
                )

            def save_instance(
                self, instance, is_create, using_transactions=True, dry_run=False
            ):
                pass

        resource = A()
        with self.assertWarns(DeprecationWarning) as w:
            resource.import_data(dataset, raise_errors=True)
            self.assertEqual(target_msg, str(w.warnings[0].message))
