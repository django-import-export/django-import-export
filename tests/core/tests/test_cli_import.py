from __future__ import unicode_literals

import os

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

from django.core.exceptions import ObjectDoesNotExist
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase


class CLIImportTest(TestCase):
    def setUp(self):
        self.output = StringIO()
        self.books_file = os.path.join(
            os.path.dirname(__file__),
            os.path.pardir,
            'exports',
            'books.csv')
        self.er_file = os.path.join(
            os.path.dirname(__file__),
            os.path.pardir,
            'exports',
            'books-with-errors.csv')
        self.no_file = os.path.join(
            os.path.dirname(__file__),
            os.path.pardir,
            'exports')

    def test_dry_run(self):
        call_command(
            'import_file',
            self.books_file,
            '--dry-run',
            '--resource-class=core.tests.test_resources.BookResource',
            '--no-color',
            stdout=self.output)
        self.assertEqual(self.output.getvalue(), 'Dry run\nOK\n')

    def test_model_name_and_totals(self):
        call_command(
            'import_file',
            self.books_file,
            '--model-name=core.Book',
            '--totals',
            '--no-color',
            stdout=self.output)
        self.assertEqual(self.output.getvalue(), '1 new\nOK\n')

    def test_nofile(self):
        with self.assertRaises(CommandError) as cm:
            call_command(
                'import_file',
                self.no_file,
                '--model-name=core.Book',
                '--no-color',
                stdout=self.output)

    def test_raise_errors(self):
        with self.assertRaises(ObjectDoesNotExist) as cm:
            call_command(
                'import_file',
                self.er_file,
                '--model-name=core.Book',
                '--raise-errors',
                '--no-color',
                stdout=self.output)
        self.assertEqual(
            cm.exception.args[0],
            'Author matching query does not exist.')

    def test_no_raise_errors(self):
        call_command(
            'import_file',
            self.er_file,
            '--model-name=core.Book',
            '--no-raise-errors',
            '--no-color',
            stdout=self.output)
        self.assertEqual(
            self.output.getvalue(),
            'Errors\nLine number: 1 - Author matching query does not exist.\n')
