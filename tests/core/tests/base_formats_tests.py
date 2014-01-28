from __future__ import unicode_literals

from django.test import TestCase
from django.utils import six

from import_export.formats import base_formats


class XLSTest(TestCase):

    def test_binary_format(self):
        self.assertTrue(base_formats.XLS().is_binary())


class CSVTest(TestCase):

    def test_binary_format(self):
        self.assertEqual(base_formats.CSV().is_binary(), not six.PY3)
