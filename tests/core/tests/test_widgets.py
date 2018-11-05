# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from decimal import Decimal
from datetime import date, datetime, time, timedelta

from django.test.utils import override_settings
from django.test import TestCase
from django.utils import timezone

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

    @override_settings(USE_TZ=True)
    def test_use_tz(self):
        self.assertEqual(self.widget.render(self.date), "13.08.2012")
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

    @override_settings(USE_TZ=True)
    def test_use_tz(self):
        self.assertEqual(self.widget.render(self.datetime),
                         "13.08.2012 18:00:00")
        aware_dt = timezone.make_aware(self.datetime,
                                       timezone.get_default_timezone())
        self.assertEqual(self.widget.clean("13.08.2012 18:00:00"),
                         aware_dt)


class DateWidgetBefore1900Test(TestCase):

    def setUp(self):
        self.date = date(1868, 8, 13)
        self.widget = widgets.DateWidget('%d.%m.%Y')

    def test_render(self):
        self.assertEqual(self.widget.render(self.date), "13.08.1868")

    def test_clean(self):
        self.assertEqual(self.widget.clean("13.08.1868"), self.date)


class TimeWidgetTest(TestCase):

    def setUp(self):
        self.time = time(20, 15, 0)
        self.widget = widgets.TimeWidget('%H:%M:%S')

    def test_render(self):
        self.assertEqual(self.widget.render(self.time), "20:15:00")

    def test_render_none(self):
        self.assertEqual(self.widget.render(None), "")

    def test_clean(self):
        self.assertEqual(self.widget.clean("20:15:00"), self.time)


class DurationWidgetTest(TestCase):

    def setUp(self):
        self.duration = timedelta(hours=1, minutes=57, seconds=0)
        self.widget = widgets.DurationWidget()

    def test_render(self):
        self.assertEqual(self.widget.render(self.duration), "1:57:00")

    def test_render_none(self):
        self.assertEqual(self.widget.render(None), "")

    def test_clean(self):
        self.assertEqual(self.widget.clean("1:57:00"), self.duration)


class FloatWidgetTest(TestCase):

    def setUp(self):
        self.value = 11.111
        self.widget = widgets.FloatWidget()

    def test_clean(self):
        self.assertEqual(self.widget.clean(11.111), self.value)

    def test_render(self):
        self.assertEqual(self.widget.render(self.value), self.value)

    def test_clean_string_zero(self):
        self.assertEqual(self.widget.clean("0"), 0.0)
        self.assertEqual(self.widget.clean("0.0"), 0.0)

    def test_clean_empty_string(self):
        self.assertEqual(self.widget.clean(""), None)
        self.assertEqual(self.widget.clean(" "), None)
        self.assertEqual(self.widget.clean("\r\n\t"), None)


class DecimalWidgetTest(TestCase):

    def setUp(self):
        self.value = Decimal("11.111")
        self.widget = widgets.DecimalWidget()

    def test_clean(self):
        self.assertEqual(self.widget.clean("11.111"), self.value)

    def test_render(self):
        self.assertEqual(self.widget.render(self.value), self.value)

    def test_clean_string_zero(self):
        self.assertEqual(self.widget.clean("0"), Decimal("0"))
        self.assertEqual(self.widget.clean("0.0"), Decimal("0"))

    def test_clean_empty_string(self):
        self.assertEqual(self.widget.clean(""), None)
        self.assertEqual(self.widget.clean(" "), None)
        self.assertEqual(self.widget.clean("\r\n\t"), None)


class IntegerWidgetTest(TestCase):

    def setUp(self):
        self.value = 0
        self.widget = widgets.IntegerWidget()

    def test_clean_integer_zero(self):
        self.assertEqual(self.widget.clean(0), self.value)

    def test_clean_string_zero(self):
        self.assertEqual(self.widget.clean("0"), self.value)
        self.assertEqual(self.widget.clean("0.0"), self.value)

    def test_clean_empty_string(self):
        self.assertEqual(self.widget.clean(""), None)
        self.assertEqual(self.widget.clean(" "), None)
        self.assertEqual(self.widget.clean("\n\t\r"), None)


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

    def test_clean_multi_column(self):
        class BirthdayWidget(widgets.ForeignKeyWidget):
            def get_queryset(self, value, row):
                return self.model.objects.filter(
                    birthday=row['birthday']
                )
        author2 = Author.objects.create(name='Foo')
        author2.birthday = "2016-01-01"
        author2.save()
        birthday_widget = BirthdayWidget(Author, 'name')
        row = {'name': "Foo", 'birthday': author2.birthday}
        self.assertEqual(birthday_widget.clean("Foo", row), author2)


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

    def test_clean_field(self):
        value = "%s,%s" % (self.cat1.name, self.cat2.name)
        cleaned_data = self.widget_name.clean(value)
        self.assertEqual(len(cleaned_data), 2)
        self.assertIn(self.cat1, cleaned_data)
        self.assertIn(self.cat2, cleaned_data)

    def test_clean_field_spaces(self):
        value = "%s, %s" % (self.cat1.name, self.cat2.name)
        cleaned_data = self.widget_name.clean(value)
        self.assertEqual(len(cleaned_data), 2)
        self.assertIn(self.cat1, cleaned_data)
        self.assertIn(self.cat2, cleaned_data)

    def test_clean_typo(self):
        value = "%s," % self.cat1.pk
        cleaned_data = self.widget.clean(value)
        self.assertEqual(len(cleaned_data), 1)
        self.assertIn(self.cat1, cleaned_data)

    def test_int(self):
        value = self.cat1.pk
        cleaned_data = self.widget.clean(value)
        self.assertEqual(len(cleaned_data), 1)
        self.assertIn(self.cat1, cleaned_data)

    def test_float(self):
        value = float(self.cat1.pk)
        cleaned_data = self.widget.clean(value)
        self.assertEqual(len(cleaned_data), 1)
        self.assertIn(self.cat1, cleaned_data)

    def test_render(self):
        self.assertEqual(self.widget.render(Category.objects),
                         "%s,%s" % (self.cat1.pk, self.cat2.pk))
        self.assertEqual(self.widget_name.render(Category.objects),
                         u"%s,%s" % (self.cat1.name, self.cat2.name))


class JSONWidgetTest(TestCase):

    def setUp(self):
        self.value = {"value": 23}
        self.widget = widgets.JSONWidget()

    def test_clean(self):
        self.assertEqual(self.widget.clean('{"value": 23}'), self.value)

    def test_render(self):
        self.assertEqual(self.widget.render(self.value), '{"value": 23}')

    def test_clean_none(self):
        self.assertEqual(self.widget.clean(None), None)
        self.assertEqual(self.widget.clean('{}'), {})

    def test_render_none(self):
        self.assertEqual(self.widget.render(None), None)
        self.assertEqual(self.widget.render(dict()), None)
