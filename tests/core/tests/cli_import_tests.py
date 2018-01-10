from __future__ import unicode_literals

import os

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

from django.core.management import call_command
from django.test import TestCase


class CLIImportTest(TestCase):
    def test_import_file_command(self):
        output = StringIO()
        filename = os.path.join(
            os.path.dirname(__file__),
            os.path.pardir,
            'exports',
            'books-dos.csv')
        call_command(
            'import_file', filename, '--model-name=core.Book', stdout=output)
