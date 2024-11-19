from core.admin import BookResource
from core.models import Book
from django.core.management import CommandError
from django.test import TestCase

from import_export.command_utils import (
    get_default_format_names,
    get_format_class,
    get_resource_class,
)
from import_export.formats import base_formats


class GetResourceClassTest(TestCase):
    def test_load_by_model(self):
        resource_class = get_resource_class("core.Book")
        self.assertIsNotNone(resource_class)
        self.assertEqual(resource_class.Meta.model, Book)

    def test_load_by_resource(self):
        resource_class = get_resource_class("core.admin.BookResource")
        self.assertEqual(resource_class, BookResource)

    def test_invalid_name(self):
        invalid_name = "invalid.model"
        with self.assertRaises(CommandError) as context:
            get_resource_class(invalid_name)
        self.assertEqual(
            str(context.exception),
            f"Cannot import '{invalid_name}' as a resource class or model.",
        )


class GetFormatClassTest(TestCase):
    def test_load_by_format_name(self):
        format_class = get_format_class("CSV", None)
        self.assertIsInstance(format_class, base_formats.CSV)

    def test_load_by_full_format_path(self):
        format_class = get_format_class("import_export.formats.base_formats.CSV", None)
        self.assertIsInstance(format_class, base_formats.CSV)

    def test_invalid_format_name(self):
        invalid_format = "EXCEL"
        with self.assertRaises(CommandError) as context:
            get_format_class(invalid_format, None)
        self.assertIn(
            "Cannot import 'EXCEL' or 'import_export.formats.base_formats.EXCEL'",
            str(context.exception),
        )

    def test_load_by_file_name_with_known_mime_type(self):
        format_class = get_format_class(None, "test.csv")
        self.assertIsInstance(format_class, base_formats.CSV)

    def test_load_by_file_name_with_unknown_mime_type(self):
        with self.assertRaises(CommandError) as context:
            get_format_class(None, "test.unknown")
        self.assertIn(
            "Cannot determine MIME type for 'test.unknown'", str(context.exception)
        )

    def test_load_by_file_name_with_no_mime_mapping(self):
        with self.assertRaises(CommandError) as context:
            get_format_class(None, "test.pdf")
        self.assertIn(
            "Cannot find format for MIME type 'application/pdf'", str(context.exception)
        )


class GetDefaultFormatNamesTest(TestCase):
    def test_get_default_format_names(self):
        format_names = get_default_format_names()
        self.assertIsInstance(format_names, str)
