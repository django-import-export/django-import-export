from django.test import TestCase

from import_export.formats import base_formats


class XLSTest(TestCase):

    def test_binary_format(self):
        self.assertTrue(base_formats.XLS().is_binary())


class CSVTest(TestCase):

    def test_binary_format(self):
        self.assertFalse(base_formats.CSV().is_binary())
