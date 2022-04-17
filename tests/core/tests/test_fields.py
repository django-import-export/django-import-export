from datetime import date

from django.test import TestCase

from import_export import fields


class Obj:

    def __init__(self, name, date=None):
        self.name = name
        self.date = date


class FieldTest(TestCase):

    def setUp(self):
        self.field = fields.Field(column_name='name', attribute='name')
        self.row = {
            'name': 'Foo',
        }
        self.obj = Obj(name='Foo', date=date(2012, 8, 13))

    def test_clean(self):
        self.assertEqual(self.field.clean(self.row),
                         self.row['name'])

    def test_clean_raises_KeyError(self):
        self.field.column_name = 'x'
        with self.assertRaisesRegex(KeyError, "Column 'x' not found in dataset. Available columns are: \\['name'\\]"):
            self.field.clean(self.row)

    def test_export(self):
        self.assertEqual(self.field.export(self.obj),
                         self.row['name'])

    def test_save(self):
        self.row['name'] = 'foo'
        self.field.save(self.obj, self.row)
        self.assertEqual(self.obj.name, 'foo')

    def test_save_follow(self):
        class Test:
            class name:
                class follow:
                    me = 'bar'

        test = Test()
        field = fields.Field(column_name='name', attribute='name__follow__me')
        row = {'name': 'foo'}
        field.save(test, row)
        self.assertEqual(test.name.follow.me, 'foo')

    def test_following_attribute(self):
        field = fields.Field(attribute='other_obj__name')
        obj2 = Obj(name="bar")
        self.obj.other_obj = obj2
        self.assertEqual(field.export(self.obj), "bar")

    def test_default(self):
        field = fields.Field(default=1, column_name='name')
        self.assertEqual(field.clean({'name': None}), 1)

    def test_default_falsy_values(self):
        field = fields.Field(default=1, column_name='name')
        self.assertEqual(field.clean({'name': 0}), 0)

    def test_default_falsy_values_without_default(self):
        field = fields.Field(column_name='name')
        self.assertEqual(field.clean({'name': 0}), 0)

    def test_saves_null_values(self):
        field = fields.Field(column_name='name', attribute='name', saves_null_values=False)
        row = {
            'name': None,
        }
        field.save(self.obj, row)
        self.assertEqual(self.obj.name, 'Foo')

        self.field.save(self.obj, row)
        self.assertIsNone(self.obj.name)

    def test_repr(self):
        self.assertEqual(repr(self.field), '<import_export.fields.Field: name>')
        self.field.column_name = None
        self.assertEqual(repr(self.field), '<import_export.fields.Field>')
