import os.path

from django.test import TestCase

from import_export.core import Importer

from .models import Book


class BookImporter(Importer):

    model = Book


class ImporterTest(TestCase):

    def setUp(self):
        self.filename = os.path.join(os.path.dirname(__file__), 'exports',
                'books.csv')

    def test_import_create(self):
        result = BookImporter(open(self.filename), dry_run=False).run()
        self.assertFalse(result.has_errors())
        self.assertEqual(Book.objects.count(), 1)

    def test_import_update(self):
        Book.objects.create(id=1, name="Other book")
        result = BookImporter(open(self.filename), dry_run=False).run()
        self.assertFalse(result.has_errors())
        self.assertEqual(Book.objects.count(), 1)
        self.assertEqual(Book.objects.all()[0].name, "Some book")
        self.assertNotEqual(result.rows[0].orig_fields[1],
                            result.rows[0].fields[1])
