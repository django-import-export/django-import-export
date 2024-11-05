import tempfile
from unittest.mock import patch
from django.core.management import call_command
from django.test import TestCase

from io import BytesIO, StringIO, TextIOWrapper
from core.models import Book

CSV_CONTENT = """\
id,name,author,author_email,imported,published,published_time,price,added,categories
1,Some book updat,,test@example.com,0,,,10.50,,1
"""


class ImportCommandTest(TestCase):
    def setUp(self):
        self.out = TextIOWrapper(BytesIO())

    def test_import_command_with_csv(self):
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".csv") as tmp_csv:
            tmp_csv.write(CSV_CONTENT)
            tmp_csv.seek(0)
            call_command("import", "core.Book", tmp_csv.name, stdout=self.out)

        self.assertEqual(Book.objects.count(), 1)

    @patch("sys.stdin", new_callable=StringIO)
    def test_import_command_with_stdin(self, mock_stdin):
        mock_stdin.write(CSV_CONTENT)
        mock_stdin.seek(0)

        call_command("import", "core.Book", "-", stdout=self.out, format="CSV")

        self.assertEqual(Book.objects.count(), 1)
