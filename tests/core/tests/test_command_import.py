import tempfile
from unittest.mock import patch
from io import BytesIO, StringIO, TextIOWrapper

from core.models import Book
from django.core.management import call_command
from django.test import TestCase

CSV_CONTENT = """\
id,name,author,author_email,imported,published,published_time,price,added,categories
1,Some book updat,,test@example.com,0,,,10.50,,1
"""

CSV_CONTENT_WITH_ERRORS = """\
id,name,author,author_email,imported,published,published_time,price,added,categories
Some book updat,,test@example.com,0,,,10.50,,1
"""


class ImportCommandTest(TestCase):
    def setUp(self):
        self.out = StringIO()
        self.err = StringIO()

    def test_import_command_with_csv(self):
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".csv") as tmp_csv:
            tmp_csv.write(CSV_CONTENT)
            tmp_csv.seek(0)
            call_command(
                "import", "core.Book", tmp_csv.name, stdout=self.out, stderr=self.err
            )

        self.assertEqual(Book.objects.count(), 1)

    @patch("sys.stdin", new_callable=lambda: TextIOWrapper(BytesIO()))
    def test_import_command_with_stdin(self, mock_stdin):
        mock_stdin.write(CSV_CONTENT)
        mock_stdin.seek(0)

        call_command(
            "import", "core.Book", "-", stdout=self.out, stderr=self.err, format="CSV"
        )

        self.assertEqual(Book.objects.count(), 1)

    def test_import_command_dry_run(self):
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".csv") as tmp_csv:
            tmp_csv.write(CSV_CONTENT)
            tmp_csv.seek(0)
            call_command(
                "import",
                "core.Book",
                tmp_csv.name,
                stdout=self.out,
                stderr=self.err,
                dry_run=True,
            )

        self.assertEqual(Book.objects.count(), 0)

    def test_import_command_errors(self):
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".csv") as tmp_csv:
            tmp_csv.write(CSV_CONTENT_WITH_ERRORS)
            tmp_csv.seek(0)
            with self.assertRaises(SystemExit):
                call_command(
                    "import",
                    "core.Book",
                    tmp_csv.name,
                    stdout=self.out,
                    stderr=self.err,
                )

        assert "Import errors!" in self.err.getvalue()
        self.assertEqual(Book.objects.count(), 0)
