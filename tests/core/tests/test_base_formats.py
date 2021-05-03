import os
from unittest import mock

import tablib
from django.test import TestCase
from django.utils.encoding import force_str
from tablib.core import UnsupportedFormat

from import_export.formats import base_formats


class FormatTest(TestCase):

    def setUp(self):
        self.format = base_formats.Format()

    @mock.patch('import_export.formats.base_formats.HTML.get_format', side_effect=ImportError)
    def test_format_non_available1(self, mocked):
        self.assertFalse(base_formats.HTML.is_available())

    @mock.patch('import_export.formats.base_formats.HTML.get_format', side_effect=UnsupportedFormat)
    def test_format_non_available2(self, mocked):
        self.assertFalse(base_formats.HTML.is_available())

    def test_format_available(self):
        self.assertTrue(base_formats.CSV.is_available())

    def test_get_title(self):
        self.assertEqual("<class 'import_export.formats.base_formats.Format'>", str(self.format.get_title()))

    def test_create_dataset_NotImplementedError(self):
        with self.assertRaises(NotImplementedError):
            self.format.create_dataset(None)

    def test_export_data_NotImplementedError(self):
        with self.assertRaises(NotImplementedError):
            self.format.export_data(None)

    def test_get_extension(self):
        self.assertEqual("", self.format.get_extension())

    def test_get_content_type(self):
        self.assertEqual("application/octet-stream", self.format.get_content_type())

    def test_is_available_default(self):
        self.assertTrue(self.format.is_available())

    def test_can_import_default(self):
        self.assertFalse(self.format.can_import())

    def test_can_export_default(self):
        self.assertFalse(self.format.can_export())

class XLSTest(TestCase):

    def setUp(self):
        self.format = base_formats.XLS()

    def test_binary_format(self):
        self.assertTrue(self.format.is_binary())

    def test_import(self):
        filename = os.path.join(
            os.path.dirname(__file__),
            os.path.pardir,
            'exports',
            'books.xls')
        with open(filename, self.format.get_read_mode()) as in_stream:
            self.format.create_dataset(in_stream.read())


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
        self.dataset = tablib.Dataset(headers=['id', 'username'])
        self.dataset.append(('1', 'x'))

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

    def test_export_data(self):
        res = self.format.export_data(self.dataset)
        self.assertEqual("id,username\r\n1,x\r\n", res)

    def test_get_extension(self):
        self.assertEqual("csv", self.format.get_extension())

    def test_content_type(self):
        self.assertEqual("text/csv", self.format.get_content_type())

    def test_can_import(self):
        self.assertTrue(self.format.can_import())

    def test_can_export(self):
        self.assertTrue(self.format.can_export())


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


class TextFormatTest(TestCase):

    def setUp(self):
        self.format = base_formats.TextFormat()

    def test_get_read_mode(self):
        self.assertEqual('r', self.format.get_read_mode())

    def test_is_binary(self):
        self.assertFalse(self.format.is_binary())