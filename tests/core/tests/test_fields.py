from datetime import date
from unittest import mock

import tablib
from core.models import Book
from core.tests.resources import BookResource
from django.test import TestCase

from import_export import fields
from import_export.exceptions import FieldError


class Obj:
    def __init__(self, name, date=None):
        self.name = name
        self.date = date


class FieldTest(TestCase):
    def setUp(self):
        self.field = fields.Field(column_name="name", attribute="name")
        self.row = {
            "name": "Foo",
        }
        self.obj = Obj(name="Foo", date=date(2012, 8, 13))

    def test_clean(self):
        self.assertEqual(self.field.clean(self.row), self.row["name"])

    def test_clean_raises_KeyError(self):
        self.field.column_name = "x"
        with self.assertRaisesRegex(
            KeyError,
            "Column 'x' not found in dataset. Available columns are: \\['name'\\]",
        ):
            self.field.clean(self.row)

    def test_export(self):
        self.assertEqual(self.field.export(self.obj), self.row["name"])

    def test_export_none(self):
        # 1872
        instance = Obj(name=None)
        self.assertEqual("", self.field.export(instance))

    def test_save(self):
        self.row["name"] = "foo"
        self.field.save(self.obj, self.row)
        self.assertEqual(self.obj.name, "foo")

    def test_save_follow(self):
        class Test:
            class name:
                class follow:
                    me = "bar"

        test = Test()
        field = fields.Field(column_name="name", attribute="name__follow__me")
        row = {"name": "foo"}
        field.save(test, row)
        self.assertEqual(test.name.follow.me, "foo")

    def test_following_attribute(self):
        field = fields.Field(attribute="other_obj__name")
        obj2 = Obj(name="bar")
        self.obj.other_obj = obj2
        self.assertEqual(field.export(self.obj), "bar")

    def test_default(self):
        field = fields.Field(default=1, column_name="name")
        self.assertEqual(field.clean({"name": None}), 1)

    def test_default_falsy_values(self):
        field = fields.Field(default=1, column_name="name")
        self.assertEqual(field.clean({"name": 0}), 0)

    def test_default_falsy_values_without_default(self):
        field = fields.Field(column_name="name")
        self.assertEqual(field.clean({"name": 0}), 0)

    def test_saves_null_values(self):
        field = fields.Field(
            column_name="name", attribute="name", saves_null_values=False
        )
        row = {
            "name": None,
        }
        field.save(self.obj, row)
        self.assertEqual(self.obj.name, "Foo")

        self.field.save(self.obj, row)
        self.assertIsNone(self.obj.name)

    def test_repr(self):
        self.assertEqual(repr(self.field), "<import_export.fields.Field: name>")
        self.field.column_name = None
        self.assertEqual(repr(self.field), "<import_export.fields.Field>")

    def testget_dehydrate_method_default(self):
        field = fields.Field(attribute="foo", column_name="bar")

        # `field_name` is the variable name defined in `Resource`
        resource_field_name = "field"
        method_name = field.get_dehydrate_method(resource_field_name)
        self.assertEqual(f"dehydrate_{resource_field_name}", method_name)

    def testget_dehydrate_method_with_custom_method_name(self):
        custom_dehydrate_method = "custom_method_name"
        field = fields.Field(
            attribute="foo", column_name="bar", dehydrate_method=custom_dehydrate_method
        )
        resource_field_name = "field"
        method_name = field.get_dehydrate_method(resource_field_name)
        self.assertEqual(method_name, custom_dehydrate_method)

    def test_get_dehydrate_method_with_callable(self):
        field = fields.Field(
            attribute="foo", column_name="bar", dehydrate_method=lambda x: x
        )
        resource_field_name = "field"
        method = field.get_dehydrate_method(resource_field_name)
        self.assertTrue(callable(method))

    def testget_dehydrate_method_without_params_raises_attribute_error(self):
        field = fields.Field(attribute="foo", column_name="bar")

        self.assertRaises(FieldError, field.get_dehydrate_method)

    def test_m2m_add_true(self):
        m2m_related_manager = mock.Mock(spec=["add", "set", "all"])
        m2m_related_manager.all.return_value = []
        self.obj.aliases = m2m_related_manager
        field = fields.Field(column_name="aliases", attribute="aliases", m2m_add=True)
        row = {
            "aliases": ["Foo", "Bar"],
        }
        field.save(self.obj, row, is_m2m=True)

        self.assertEqual(m2m_related_manager.add.call_count, 1)
        self.assertEqual(m2m_related_manager.set.call_count, 0)
        m2m_related_manager.add.assert_called_once_with("Foo", "Bar")

        row = {
            "aliases": ["apple"],
        }
        field.save(self.obj, row, is_m2m=True)
        m2m_related_manager.add.assert_called_with("apple")

    def test_m2m_add_False(self):
        m2m_related_manager = mock.Mock(spec=["add", "set", "all"])
        self.obj.aliases = m2m_related_manager
        field = fields.Field(column_name="aliases", attribute="aliases")
        row = {
            "aliases": ["Foo", "Bar"],
        }
        field.save(self.obj, row, is_m2m=True)

        self.assertEqual(m2m_related_manager.add.call_count, 0)
        self.assertEqual(m2m_related_manager.set.call_count, 1)
        m2m_related_manager.set.assert_called_once_with(["Foo", "Bar"])

    def test_get_value_with_callable(self):
        class CallableValue:
            def __call__(self):
                return "some val"

        self.obj.name = CallableValue()
        val = self.field.get_value(self.obj)
        self.assertEqual("some val", val)

    def test_get_value_with_no_attribute(self):
        self.field.attribute = None
        self.assertIsNone(self.field.get_value(self.obj))

    def test_import_null_django_CharField_saved_as_empty_string(self):
        # issue 1485
        resource = BookResource()
        self.assertTrue(resource._meta.model.author_email.field.blank)
        self.assertFalse(resource._meta.model.author_email.field.null)
        headers = ["id", "author_email"]
        row = [1, None]
        dataset = tablib.Dataset(row, headers=headers)
        resource.import_data(dataset, raise_errors=True)
        book = Book.objects.get(id=1)
        self.assertEqual("", book.author_email)

    def test_import_empty_django_CharField_saved_as_empty_string(self):
        resource = BookResource()
        self.assertTrue(resource._meta.model.author_email.field.blank)
        self.assertFalse(resource._meta.model.author_email.field.null)
        headers = ["id", "author_email"]
        row = [1, ""]
        dataset = tablib.Dataset(row, headers=headers)
        resource.import_data(dataset, raise_errors=True)
        book = Book.objects.get(id=1)
        self.assertEqual("", book.author_email)
