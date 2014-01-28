from __future__ import unicode_literals

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

    def test_following_attribute(self):
        field = fields.Field(attribute='other_obj__name')
        obj2 = Obj(name="bar")
        self.obj.other_obj = obj2
        self.assertEqual(field.export(self.obj), "bar")
