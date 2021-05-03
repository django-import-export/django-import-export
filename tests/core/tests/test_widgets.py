from datetime import date, datetime, time, timedelta
from decimal import Decimal
from unittest import mock

import pytz
from core.models import Author, Category
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import timezone

from import_export import widgets


class BooleanWidgetTest(TestCase):

    def setUp(self):
        self.widget = widgets.BooleanWidget()

    def test_clean(self):
        self.assertTrue(self.widget.clean("1"))
        self.assertTrue(self.widget.clean(1))
        self.assertTrue(self.widget.clean("TRUE"))
        self.assertTrue(self.widget.clean("True"))
        self.assertTrue(self.widget.clean("true"))

        self.assertFalse(self.widget.clean("0"))
        self.assertFalse(self.widget.clean(0))
        self.assertFalse(self.widget.clean("FALSE"))
        self.assertFalse(self.widget.clean("False"))
        self.assertFalse(self.widget.clean("false"))

        self.assertEqual(self.widget.clean(""), None)
        self.assertEqual(self.widget.clean("NONE"), None)
        self.assertEqual(self.widget.clean("None"), None)
        self.assertEqual(self.widget.clean("none"), None)
        self.assertEqual(self.widget.clean("NULL"), None)
        self.assertEqual(self.widget.clean("null"), None)

    def test_render(self):
        self.assertEqual(self.widget.render(True), "1")
        self.assertEqual(self.widget.render(False), "0")
        self.assertEqual(self.widget.render(None), "")


class DateWidgetTest(TestCase):

    def setUp(self):
        self.date = date(2012, 8, 13)
        self.widget = widgets.DateWidget('%d.%m.%Y')

    def test_render(self):
        self.assertEqual(self.widget.render(self.date), "13.08.2012")

    def test_render_none(self):
        self.assertEqual(self.widget.render(None), "")

    def test_render_datetime_safe(self):
        """datetime_safe is supposed to be used to support dates older than 1000"""
        self.date = date(10, 8, 2)
        self.assertEqual(self.widget.render(self.date), "02.08.0010")

    def test_clean(self):
        self.assertEqual(self.widget.clean("13.08.2012"), self.date)

    def test_clean_returns_None_for_empty_value(self):
        self.assertIsNone(self.widget.clean(None))

    def test_clean_returns_date_when_date_passed(self):
        self.assertEqual(self.date, self.widget.clean(self.date))

    def test_clean_raises_ValueError(self):
        self.widget = widgets.DateWidget('x')
        with self.assertRaisesRegex(ValueError, "Enter a valid date."):
            self.widget.clean('2021-05-01')

    @override_settings(USE_TZ=True)
    def test_use_tz(self):
        self.assertEqual(self.widget.render(self.date), "13.08.2012")
        self.assertEqual(self.widget.clean("13.08.2012"), self.date)

    @override_settings(DATE_INPUT_FORMATS=None)
    def test_default_format(self):
        self.widget = widgets.DateWidget()
        self.assertEqual(("%Y-%m-%d",), self.widget.formats)


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

    @override_settings(USE_TZ=True, TIME_ZONE='Europe/Ljubljana')
    def test_use_tz(self):
        utc_dt = timezone.make_aware(self.datetime, pytz.UTC)
        self.assertEqual(self.widget.render(utc_dt), "13.08.2012 20:00:00")
        self.assertEqual(self.widget.clean("13.08.2012 20:00:00"), utc_dt)

    @override_settings(DATETIME_INPUT_FORMATS=None)
    def test_default_format(self):
        self.widget = widgets.DateTimeWidget()
        self.assertEqual(("%Y-%m-%d %H:%M:%S",), self.widget.formats)

    def test_clean_returns_datetime_when_datetime_passed(self):
        self.assertEqual(self.datetime, self.widget.clean(self.datetime))

    def test_render_datetime_safe(self):
        """datetime_safe is supposed to be used to support dates older than 1000"""
        self.datetime = datetime(10, 8, 2)
        self.assertEqual(self.widget.render(self.datetime), "02.08.0010 00:00:00")


class DateWidgetBefore1900Test(TestCase):
    """https://github.com/django-import-export/django-import-export/pull/94"""
    def setUp(self):
        self.date = date(1868, 8, 13)
        self.widget = widgets.DateWidget('%d.%m.%Y')

    def test_render(self):
        self.assertEqual(self.widget.render(self.date), "13.08.1868")

    def test_clean(self):
        self.assertEqual(self.widget.clean("13.08.1868"), self.date)


class DateTimeWidgetBefore1900Test(TestCase):

    def setUp(self):
        self.datetime = datetime(1868, 8, 13)
        self.widget = widgets.DateTimeWidget('%d.%m.%Y')

    def test_render(self):
        self.assertEqual("13.08.1868", self.widget.render(self.datetime))

    def test_clean(self):
        self.assertEqual(self.datetime, self.widget.clean("13.08.1868"))


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

    @override_settings(TIME_INPUT_FORMATS=None)
    def test_default_format(self):
        self.widget = widgets.TimeWidget()
        self.assertEqual(("%H:%M:%S",), self.widget.formats)

    def test_clean_raises_ValueError(self):
        self.widget = widgets.TimeWidget('x')
        with self.assertRaisesRegex(ValueError, "Enter a valid time."):
            self.widget.clean("20:15:00")


class DurationWidgetTest(TestCase):

    def setUp(self):
        self.duration = timedelta(hours=1, minutes=57, seconds=0)
        self.widget = widgets.DurationWidget()

    def test_render(self):
        self.assertEqual(self.widget.render(self.duration), "1:57:00")

    def test_render_none(self):
        self.assertEqual(self.widget.render(None), "")

    def test_render_zero(self):
        self.assertEqual(self.widget.render(timedelta(0)), "0:00:00")

    def test_clean(self):
        self.assertEqual(self.widget.clean("1:57:00"), self.duration)

    def test_clean_none(self):
        self.assertEqual(self.widget.clean(""), None)

    def test_clean_zero(self):
        self.assertEqual(self.widget.clean("0:00:00"), timedelta(0))

    @mock.patch("import_export.widgets.parse_duration", side_effect=ValueError("err"))
    def test_clean_raises_ValueError(self, _):
        with self.assertRaisesRegex(ValueError, "Enter a valid duration."):
            self.widget.clean("x")


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
        self.assertEqual(self.widget.clean(11.111), self.value)

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
        self.assertEqual(self.widget.clean(self.author.id), self.author)

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

    def test_render_handles_value_error(self):
        class TestObj(object):
            @property
            def attr(self):
                raise ValueError("some error")

        t = TestObj()
        self.widget = widgets.ForeignKeyWidget(mock.Mock(), "attr")
        self.assertIsNone(self.widget.render(t))



class ManyToManyWidget(TestCase):

    def setUp(self):
        self.widget = widgets.ManyToManyWidget(Category)
        self.widget_name = widgets.ManyToManyWidget(Category, field="name")
        self.cat1 = Category.objects.create(name='Cat úňíčóďě')
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

    @mock.patch("core.models.Category.objects.none")
    def test_clean_handles_None_value(self, mock_none):
        self.widget.clean(None)
        self.assertEqual(1, mock_none.call_count)

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
        self.assertEqual(self.widget.render(Category.objects.order_by('id')),
                         "%s,%s" % (self.cat1.pk, self.cat2.pk))
        self.assertEqual(self.widget_name.render(Category.objects.order_by('id')),
                         "%s,%s" % (self.cat1.name, self.cat2.name))


class JSONWidgetTest(TestCase):

    def setUp(self):
        self.value = {"value": 23}
        self.widget = widgets.JSONWidget()

    def test_clean(self):
        self.assertEqual(self.widget.clean('{"value": 23}'), self.value)

    def test_render(self):
        self.assertEqual(self.widget.render(self.value), '{"value": 23}')

    def test_clean_single_quoted_string(self):
        self.assertEqual(self.widget.clean("{'value': 23}"), self.value)
        self.assertEqual(self.widget.clean("{'value': null}"), {'value': None})

    def test_clean_none(self):
        self.assertEqual(self.widget.clean(None), None)
        self.assertEqual(self.widget.clean('{"value": null}'), {'value': None})

    def test_render_none(self):
        self.assertEqual(self.widget.render(None), None)
        self.assertEqual(self.widget.render(dict()), None)
        self.assertEqual(self.widget.render({"value": None}), '{"value": null}')


class SimpleArrayWidgetTest(TestCase):

    def setUp(self):
        self.value = {"value": 23}
        self.widget = widgets.SimpleArrayWidget()

    def test_default_separator(self):
        self.assertEqual(',', self.widget.separator)

    def test_arg_separator(self):
        self.widget = widgets.SimpleArrayWidget('|')
        self.assertEqual('|', self.widget.separator)

    def test_clean_splits_str(self):
        s = "a,b,c"
        self.assertEqual(["a", "b", "c"], self.widget.clean(s))

    def test_clean_returns_empty_list_for_empty_arg(self):
        s = ''
        self.assertEqual([], self.widget.clean(s))

    def test_render(self):
        v = ["a", "b", "c"]
        s = "a,b,c"
        self.assertEqual(s, self.widget.render(v))