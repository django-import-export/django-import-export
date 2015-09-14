from __future__ import unicode_literals

import os

from django.test import TestCase

from import_export.formats import base_formats


class XLSTest(TestCase):

    def test_binary_format(self):
        self.assertTrue(base_formats.XLS().is_binary())


class CSVTest(TestCase):

    def setUp(self):
        self.format = base_formats.CSV()

    def test_import_dos(self):
        filename = os.path.join(
            os.path.dirname(__file__),
            os.path.pardir,
            'exports',
            'books-dos.csv')
        in_stream = open(filename, self.format.get_read_mode()).read()
        expected = 'id,name,author_email\n1,Some book,test@example.com\n'
        self.assertEqual(in_stream, expected)
