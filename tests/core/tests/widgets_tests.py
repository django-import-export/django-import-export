# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from decimal import Decimal
from datetime import date, datetime

from django.test import TestCase

from import_export import widgets

from core.models import (
    Author,
    Category,
)


class BooleanWidgetTest(TestCase):

    def setUp(self):
        self.widget = widgets.BooleanWidget()

    def test_clean(self):
        self.assertTrue(self.widget.clean("1"))
        self.assertTrue(self.widget.clean(1))
        self.assertEqual(self.widget.clean(""), None)

    def test_render(self):
        self.assertEqual(self.widget.render(None), "")


class DateWidgetTest(TestCase):

    def setUp(self):
        self.date = date(2012, 8, 13)
        self.widget = widgets.DateWidget('%d.%m.%Y')

    def test_render(self):
        self.assertEqual(self.widget.render(self.date), "13.08.2012")

    def test_render_none(self):
        self.assertEqual(self.widget.render(None), "")

    def test_clean(self):
        self.assertEqual(self.widget.clean("13.08.2012"), self.date)


class DateTimeWidgetTest(TestCase):

    def setUp(self):
        self.datetime = datetime(2012, 8, 13, 18, 0, 0)
        self.widget = widgets.DateTimeWidget('%d.%m.%Y %H:%M:%S')

    def test_render(self):
        self.assertEqual(self.widget.render(self.datetime),
                         "13.08.2012 18:00:00")

    def test_render_none(self):
        self.assertEqual(self.widget.render(None), "")

    def test_clean(self):
        self.assertEqual(self.widget.clean("13.08.2012 18:00:00"),
                         self.datetime)


class DateWidgetBefore1900Test(TestCase):

    def setUp(self):
        self.date = date(1868, 8, 13)
        self.widget = widgets.DateWidget('%d.%m.%Y')

    def test_render(self):
        self.assertEqual(self.widget.render(self.date), "13.08.1868")

    def test_clean(self):
        self.assertEqual(self.widget.clean("13.08.1868"), self.date)


class DecimalWidgetTest(TestCase):

    def setUp(self):
        self.value = Decimal("11.111")
        self.widget = widgets.DecimalWidget()

    def test_clean(self):
        self.assertEqual(self.widget.clean("11.111"), self.value)

    def test_render(self):
        self.assertEqual(self.widget.render(self.value), self.value)


class ForeignKeyWidgetTest(TestCase):

    def setUp(self):
        self.widget = widgets.ForeignKeyWidget(Author)
        self.author = Author.objects.create(name='Foo')

    def test_clean(self):
        self.assertEqual(self.widget.clean(1), self.author)

    def test_clean_empty(self):
        self.assertEqual(self.widget.clean(""), None)

    def test_render(self):
        self.assertEqual(self.widget.render(self.author), self.author.pk)

    def test_render_empty(self):
        self.assertEqual(self.widget.render(None), "")


class ManyToManyWidget(TestCase):

    def setUp(self):
        self.widget = widgets.ManyToManyWidget(Category)
        self.widget_name = widgets.ManyToManyWidget(Category, field="name")
        self.cat1 = Category.objects.create(name=u'Cat úňíčóďě')
        self.cat2 = Category.objects.create(name='Cat 2')

    def test_clean(self):
        value = "%s,%s" % (self.cat1.pk, self.cat2.pk)
        cleaned_data = self.widget.clean(value)
        self.assertEqual(len(cleaned_data), 2)
        self.assertIn(self.cat1, cleaned_data)
        self.assertIn(self.cat2, cleaned_data)

    def test_render(self):
        self.assertEqual(self.widget.render(Category.objects),
                "%s,%s" % (self.cat1.pk, self.cat2.pk))
        self.assertEqual(self.widget_name.render(Category.objects),
                u"%s,%s" % (self.cat1.name, self.cat2.name))

