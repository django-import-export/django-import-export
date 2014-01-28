from __future__ import unicode_literals

import warnings
import tablib

try:
    from tablib.compat import xlrd
    XLS_IMPORT = True
except ImportError:
    try:
        import xlrd # NOQA
        XLS_IMPORT = True
    except ImportError:
        xls_warning = "Installed `tablib` library does not include"
        "import support for 'xls' format and xlrd module is not found."
        warnings.warn(xls_warning, ImportWarning)
        XLS_IMPORT = False

from django.utils.importlib import import_module
from django.utils import six


class Format(object):

    def get_title(self):
        return type(self)

    def create_dataset(self, in_stream):
        """
        Create dataset from given string.
        """
        raise NotImplementedError()

    def export_data(self, dataset):
        """
        Returns format representation for given dataset.
        """
        raise NotImplementedError()

    def is_binary(self):
        """
        Returns if this format is binary.
        """
        return True

    def get_read_mode(self):
        """
        Returns mode for opening files.
        """
        return 'rb'

    def get_extension(self):
        """
        Returns extension for this format files.
        """
        return ""

    def can_import(self):
        return False

    def can_export(self):
        return False


class TablibFormat(Format):
    TABLIB_MODULE = None

    def get_format(self):
        """
        Import and returns tablib module.
        """
        return import_module(self.TABLIB_MODULE)

    def get_title(self):
        return self.get_format().title

    def create_dataset(self, in_stream):
        data = tablib.Dataset()
        self.get_format().import_set(data, in_stream)
        return data

    def export_data(self, dataset):
        return self.get_format().export_set(dataset)

    def get_extension(self):
        # we support both 'extentions' and 'extensions' because currently tablib's master
        # branch uses 'extentions' (which is a typo) but it's dev branch already uses 'extension'.
        # TODO - remove this once the typo is fixxed in tablib's master branch
        if hasattr(self.get_format(), 'extentions'):
            return self.get_format().extentions[0]
        return self.get_format().extensions[0]

    def can_import(self):
        return hasattr(self.get_format(), 'import_set')

    def can_export(self):
        return hasattr(self.get_format(), 'export_set')


class TextFormat(TablibFormat):

    def get_read_mode(self):
        return 'rU'

    def is_binary(self):
        return False


class CSV(TablibFormat):
    """
    CSV is treated as binary in Python 2.
    """
    TABLIB_MODULE = 'tablib.formats._csv'

    def get_read_mode(self):
        return 'rU' if six.PY3 else 'rb'

    def is_binary(self):
        return False if six.PY3 else True


class JSON(TextFormat):
    TABLIB_MODULE = 'tablib.formats._json'


class YAML(TextFormat):
    TABLIB_MODULE = 'tablib.formats._yaml'


class TSV(TextFormat):
    TABLIB_MODULE = 'tablib.formats._tsv'


class ODS(TextFormat):
    TABLIB_MODULE = 'tablib.formats._ods'


class XLSX(TextFormat):
    TABLIB_MODULE = 'tablib.formats._xlsx'


class HTML(TextFormat):
    TABLIB_MODULE = 'tablib.formats._html'


class XLS(TablibFormat):
    TABLIB_MODULE = 'tablib.formats._xls'

    def can_import(self):
        return XLS_IMPORT

    def create_dataset(self, in_stream):
        """
        Create dataset from first sheet.
        """
        assert XLS_IMPORT
        xls_book = xlrd.open_workbook(file_contents=in_stream)
        dataset = tablib.Dataset()
        sheet = xls_book.sheets()[0]
        for i in xrange(sheet.nrows):
            if i == 0:
                dataset.headers = sheet.row_values(0)
            else:
                dataset.append(sheet.row_values(i))
        return dataset
