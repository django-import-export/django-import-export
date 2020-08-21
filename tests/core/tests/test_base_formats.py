import os
from tablib.core import UnsupportedFormat
from unittest import mock

from django.test import TestCase
from django.utils.encoding import force_str

from import_export.formats import base_formats


class FormatTest(TestCase):

    @mock.patch('import_export.formats.base_formats.HTML.get_format', side_effect=ImportError)
    def test_format_non_available1(self, mocked):
        self.assertFalse(base_formats.HTML.is_available())

    @mock.patch('import_export.formats.base_formats.HTML.get_format', side_effect=UnsupportedFormat)
    def test_format_non_available2(self, mocked):
        self.assertFalse(base_formats.HTML.is_available())

    def test_format_available(self):
        self.assertTrue(base_formats.CSV.is_available())


class XLSTest(TestCase):

    def test_binary_format(self):
        self.assertTrue(base_formats.XLS().is_binary())


class XLSXTest(TestCase):

    def setUp(self):
        self.format = base_formats.XLSX()

    def test_binary_format(self):
        self.assertTrue(self.format.is_binary())

    def test_import(self):
        filename = os.path.join(
            os.path.dirname(__file__),
            os.path.pardir,
            'exports',
            'books.xlsx')
        with open(filename, self.format.get_read_mode()) as in_stream:
            self.format.create_dataset(in_stream.read())


class CSVTest(TestCase):

    def setUp(self):
        self.format = base_formats.CSV()

    def test_import_dos(self):
        filename = os.path.join(
            os.path.dirname(__file__),
            os.path.pardir,
            'exports',
            'books-dos.csv')
        with open(filename, self.format.get_read_mode()) as in_stream:
            actual = in_stream.read()
        expected = 'id,name,author_email\n1,Some book,test@example.com\n'
        self.assertEqual(actual, expected)

    def test_import_mac(self):
        filename = os.path.join(
            os.path.dirname(__file__),
            os.path.pardir,
            'exports',
            'books-mac.csv')
        with open(filename, self.format.get_read_mode()) as in_stream:
            actual = in_stream.read()
        expected = 'id,name,author_email\n1,Some book,test@example.com\n'
        self.assertEqual(actual, expected)

    def test_import_unicode(self):
        # importing csv UnicodeEncodeError 347
        filename = os.path.join(
            os.path.dirname(__file__),
            os.path.pardir,
            'exports',
            'books-unicode.csv')
        with open(filename, self.format.get_read_mode()) as in_stream:
            data = force_str(in_stream.read())
        base_formats.CSV().create_dataset(data)


class TSVTest(TestCase):

    def setUp(self):
        self.format = base_formats.TSV()

    def test_import_mac(self):
        filename = os.path.join(
            os.path.dirname(__file__),
            os.path.pardir,
            'exports',
            'books-mac.tsv')
        with open(filename, self.format.get_read_mode()) as in_stream:
            actual = in_stream.read()
        expected = 'id\tname\tauthor_email\n1\tSome book\ttest@example.com\n'
        self.assertEqual(actual, expected)

    def test_import_unicode(self):
        # importing tsv UnicodeEncodeError
        filename = os.path.join(
            os.path.dirname(__file__),
            os.path.pardir,
            'exports',
            'books-unicode.tsv')
        with open(filename, self.format.get_read_mode()) as in_stream:
            data = force_str(in_stream.read())
        base_formats.TSV().create_dataset(data)
