from io import BytesIO, TextIOWrapper

from core.models import Book
from django.core.management import call_command
from django.test import TestCase


class ExportCommandTest(TestCase):
    def setUp(self):
        self.out = TextIOWrapper(BytesIO())

    def test_export_command_as_csv(self):
        Book.objects.create(id=100, name="Some book")

        call_command("export", "CSV", "core.Book", stdout=self.out)

        self.out.seek(0)
        data = self.out.read()
        self.assertEqual(
            data,
            "id,name,author,author_email,imported,published,published_time,price,added,categories\n100,Some book,,,0,,,,,\n",  # noqa
        )

    def test_export_command_as_csv_with_encoding(self):
        Book.objects.create(id=100, name="Some book")

        call_command("export", "CSV", "core.Book", stdout=self.out, encoding="cp1250")

        self.out.seek(0)
        data = self.out.read()
        self.assertEqual(
            data,
            "id,name,author,author_email,imported,published,published_time,price,added,categories\n100,Some book,,,0,,,,,\n",  # noqa
        )
