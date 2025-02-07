import tempfile
from io import BytesIO, StringIO, TextIOWrapper
from unittest import mock
from unittest.mock import patch

from core.models import Book
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from import_export.formats.base_formats import XLSX
from import_export.resources import ModelResource, modelresource_factory

CSV_CONTENT = """\
id,name,author,author_email,imported,published,published_time,price,added,categories
1,Some book updat,,test@example.com,0,,,10.50,,1
"""

CSV_CONTENT_WITH_ERRORS = """\
id,name,author,author_email,imported,published,published_time,price,added,categories
Some book updat,,test@example.com,0,,,10.50,,1
"""


class BookResourceWithError(ModelResource):
    def before_import(self, *args, **kwargs):
        raise Exception("Import base errors")

    class Meta:
        model = Book


class ImportCommandTest(TestCase):
    def setUp(self):
        self.out = StringIO()
        self.err = StringIO()

    def test_import_command_with_csv(self):
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".csv") as tmp_csv:
            tmp_csv.write(CSV_CONTENT)
            tmp_csv.seek(0)
            call_command(
                "import",
                "core.Book",
                tmp_csv.name,
                stdout=self.out,
                stderr=self.err,
                interactive=False,
            )

        self.assertEqual(Book.objects.count(), 1)

    @patch("sys.stdin", new_callable=lambda: TextIOWrapper(BytesIO()))
    def test_import_command_with_stdin(self, mock_stdin):
        mock_stdin.write(CSV_CONTENT)
        mock_stdin.seek(0)

        call_command(
            "import",
            "core.Book",
            "-",
            stdout=self.out,
            stderr=self.err,
            format="CSV",
            interactive=False,
        )

        self.assertEqual(Book.objects.count(), 1)

    @patch("sys.stdin", new_callable=lambda: TextIOWrapper(BytesIO()))
    def test_import_command_with_stdin_binary_format(self, mock_stdin):
        # create binary export data
        resource = modelresource_factory(Book)()
        data = resource.export()
        export_data = XLSX().export_data(data)
        mock_stdin.buffer.write(export_data)
        mock_stdin.seek(0)

        call_command(
            "import",
            "core.Book",
            "-",
            stdout=self.out,
            stderr=self.err,
            format="XLSX",
            interactive=False,
        )

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
                interactive=False,
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
                    interactive=False,
                )

        assert "Import errors!" in self.err.getvalue()
        self.assertEqual(Book.objects.count(), 0)

    def test_import_command_with_base_errors(self):
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".csv") as tmp_csv:
            tmp_csv.write(CSV_CONTENT)
            tmp_csv.seek(0)
            with self.assertRaises(SystemExit):
                call_command(
                    "import",
                    "core.tests.test_command_import.BookResourceWithError",
                    tmp_csv.name,
                    stdout=self.out,
                    stderr=self.err,
                    interactive=False,
                )

            assert "Import base errors" in self.err.getvalue()
            self.assertEqual(Book.objects.count(), 0)

    def test_import_command_interactive(self):
        with mock.patch("builtins.input", side_effect=lambda msg: "no"):
            with tempfile.NamedTemporaryFile(mode="w+", suffix=".csv") as tmp_csv:
                tmp_csv.write(CSV_CONTENT)
                tmp_csv.seek(0)
                with self.assertRaises(CommandError) as e:
                    call_command(
                        "import",
                        "core.Book",
                        tmp_csv.name,
                        stdout=self.out,
                        stderr=self.err,
                    )
                    assert e.exception.args[0] == "Import cancelled."

        self.assertEqual(Book.objects.count(), 0)
