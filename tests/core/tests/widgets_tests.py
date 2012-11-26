from datetime import date

from django.test import TestCase

from import_export import widgets


class DateWidgetTest(TestCase):

    def setUp(self):
        self.date = date(2012, 8, 13)
        self.widget = widgets.DateWidget('%d.%m.%Y')

    def test_render(self):
        self.assertEqual(self.widget.render(self.date), "13.08.2012")

    def test_clean(self):
        self.assertEqual(self.widget.clean("13.08.2012"), self.date)
