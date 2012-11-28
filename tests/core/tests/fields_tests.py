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

    def test_export(self):
        self.assertEqual(self.field.export(self.obj),
                self.row['name'])

    def test_save(self):
        self.row['name'] = 'foo'
        self.field.save(self.obj, self.row)
        self.assertEqual(self.obj.name, 'foo')


class IntegerFieldTest(TestCase):

    def setUp(self):
        self.field = fields.IntegerField(column_name='name', attribute='name')

    def test_clean(self):
        row = {'name': ""}
        self.assertEqual(self.field.clean(row), None)

    def test_export(self):
        obj = Obj(name=None)
        self.assertEqual(self.field.export(obj), "")
