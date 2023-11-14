from datetime import datetime
from io import BytesIO
from unittest import mock
from unittest.mock import MagicMock

import chardet
import tablib
from core.models import Author, Book
from core.tests.admin_integration.mixins import AdminTestMixin
from core.tests.utils import ignore_widget_deprecation_warning
from django.http import HttpRequest
from django.test.testcases import TestCase
from django.test.utils import override_settings
from openpyxl.reader.excel import load_workbook
from tablib import Dataset

from import_export import formats
from import_export.admin import ExportActionMixin, ExportMixin
from import_export.formats.base_formats import XLSX


class ExportAdminIntegrationTest(AdminTestMixin, TestCase):
    def test_export(self):
        response = self.client.get("/admin/core/book/export/")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Export 0 selected items.", str(response.content))
        form = response.context["form"]
        self.assertEqual(2, len(form.fields["resource"].choices))

        data = {
            "file_format": "0",
        }
        date_str = datetime.now().strftime("%Y-%m-%d")
        response = self.client.post("/admin/core/book/export/", data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.has_header("Content-Disposition"))
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertEqual(
            response["Content-Disposition"],
            'attachment; filename="Book-{}.csv"'.format(date_str),
        )
        self.assertEqual(
            b"id,name,author,author_email,imported,published,"
            b"published_time,price,added,categories\r\n",
            response.content,
        )

    def test_get_export_form_single_resource(self):
        response = self.client.get("/admin/core/category/export/")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Export 0 selected items.", str(response.content))
        form = response.context["form"]
        self.assertEqual(0, len(form.fields["resource"].choices))
        self.assertTrue(form.fields["resource"].widget.attrs["readonly"])
        self.assertIn("CategoryResource", str(response.content))
        self.assertNotIn('select name="resource"', str(response.content))

    def test_export_second_resource(self):
        response = self.client.get("/admin/core/book/export/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Export/Import only book names")

        data = {
            "file_format": "0",
            "resource": 1,
        }
        date_str = datetime.now().strftime("%Y-%m-%d")
        response = self.client.post("/admin/core/book/export/", data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.has_header("Content-Disposition"))
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertEqual(
            response["Content-Disposition"],
            'attachment; filename="Book-{}.csv"'.format(date_str),
        )
        self.assertEqual(b"id,name\r\n", response.content)

    @override_settings(EXPORT_FORMATS=[XLSX])
    def test_get_export_form_single_format(self):
        response = self.client.get("/admin/core/category/export/")
        form = response.context["form"]
        self.assertEqual(1, len(form.fields["file_format"].choices))
        self.assertTrue(form.fields["file_format"].widget.attrs["readonly"])
        self.assertIn("xlsx", str(response.content))
        self.assertNotIn('select name="file_format"', str(response.content))

    @override_settings(EXPORT_FORMATS=[])
    def test_export_empty_export_formats(self):
        with self.assertRaisesRegex(ValueError, "invalid export formats list"):
            self.client.get("/admin/core/category/export/")

    def test_returns_xlsx_export(self):
        response = self.client.get("/admin/core/book/export/")
        self.assertEqual(response.status_code, 200)

        xlsx_index = self._get_input_format_index("xlsx")
        data = {"file_format": str(xlsx_index)}
        response = self.client.post("/admin/core/book/export/", data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.has_header("Content-Disposition"))
        self.assertEqual(
            response["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    @override_settings(IMPORT_EXPORT_ESCAPE_FORMULAE_ON_EXPORT=True)
    @ignore_widget_deprecation_warning
    def test_export_escape_formulae(self):
        Book.objects.create(id=1, name="=SUM(1+1)")
        Book.objects.create(id=2, name="<script>alert(1)</script>")
        response = self.client.get("/admin/core/book/export/")
        self.assertEqual(response.status_code, 200)

        xlsx_index = self._get_input_format_index("xlsx")
        data = {"file_format": str(xlsx_index)}
        response = self.client.post("/admin/core/book/export/", data)
        self.assertEqual(response.status_code, 200)
        content = response.content
        wb = load_workbook(filename=BytesIO(content))
        self.assertEqual("<script>alert(1)</script>", wb.active["B2"].value)
        self.assertEqual("SUM(1+1)", wb.active["B3"].value)

    @override_settings(IMPORT_EXPORT_ESCAPE_FORMULAE_ON_EXPORT=True)
    @ignore_widget_deprecation_warning
    def test_export_escape_formulae_csv(self):
        b1 = Book.objects.create(id=1, name="=SUM(1+1)")
        response = self.client.get("/admin/core/book/export/")
        self.assertEqual(response.status_code, 200)

        index = self._get_input_format_index("csv")
        data = {"file_format": str(index)}
        response = self.client.post("/admin/core/book/export/", data)
        self.assertIn(
            f"{b1.id},SUM(1+1),,,0,,,,,\r\n".encode(),
            response.content,
        )

    @override_settings(IMPORT_EXPORT_ESCAPE_FORMULAE_ON_EXPORT=False)
    @ignore_widget_deprecation_warning
    def test_export_escape_formulae_csv_false(self):
        b1 = Book.objects.create(id=1, name="=SUM(1+1)")
        response = self.client.get("/admin/core/book/export/")
        self.assertEqual(response.status_code, 200)

        index = self._get_input_format_index("csv")
        data = {"file_format": str(index)}
        response = self.client.post("/admin/core/book/export/", data)
        self.assertIn(
            f"{b1.id},=SUM(1+1),,,0,,,,,\r\n".encode(),
            response.content,
        )


class FilteredExportAdminIntegrationTest(AdminTestMixin, TestCase):
    fixtures = ["category", "book", "author"]

    @ignore_widget_deprecation_warning
    def test_export_filters_by_form_param(self):
        # issue 1578
        author = Author.objects.get(name="Ian Fleming")

        data = {"file_format": "0", "author": str(author.id)}
        date_str = datetime.now().strftime("%Y-%m-%d")
        response = self.client.post("/admin/core/ebook/export/", data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.has_header("Content-Disposition"))
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertEqual(
            response["Content-Disposition"],
            'attachment; filename="EBook-{}.csv"'.format(date_str),
        )
        self.assertEqual(
            b"id,name,author,author_email,imported,published,"
            b"published_time,price,added,categories\r\n"
            b"5,The Man with the Golden Gun,5,ian@example.com,"
            b"0,1965-04-01,21:00:00,5.00,,2\r\n",
            response.content,
        )


class TestExportEncoding(TestCase):
    mock_request = MagicMock(spec=HttpRequest)
    mock_request.POST = {"file_format": 0}

    class TestMixin(ExportMixin):
        model = Book

        def __init__(self, test_str=None):
            self.test_str = test_str

        def get_data_for_export(self, request, queryset, *args, **kwargs):
            dataset = Dataset(headers=["id", "name"])
            dataset.append([1, self.test_str])
            return dataset

        def get_export_queryset(self, request):
            return list()

        def get_export_filename(self, request, queryset, file_format):
            return "f"

    def setUp(self):
        self.file_format = formats.base_formats.CSV()
        self.export_mixin = self.TestMixin(test_str="teststr")

    def test_to_encoding_not_set_default_encoding_is_utf8(self):
        self.export_mixin = self.TestMixin(test_str="teststr")
        data = self.export_mixin.get_export_data(
            self.file_format, list(), request=self.mock_request
        )
        csv_dataset = tablib.import_set(data)
        self.assertEqual("teststr", csv_dataset.dict[0]["name"])

    def test_to_encoding_set(self):
        self.export_mixin = self.TestMixin(test_str="ハローワールド")
        data = self.export_mixin.get_export_data(
            self.file_format, list(), request=self.mock_request, encoding="shift-jis"
        )
        encoding = chardet.detect(bytes(data))["encoding"]
        self.assertEqual("SHIFT_JIS", encoding)

    def test_to_encoding_set_incorrect(self):
        self.export_mixin = self.TestMixin()
        with self.assertRaises(LookupError):
            self.export_mixin.get_export_data(
                self.file_format,
                list(),
                request=self.mock_request,
                encoding="bad-encoding",
            )

    def test_to_encoding_not_set_for_binary_file(self):
        self.export_mixin = self.TestMixin(test_str="teststr")
        self.file_format = formats.base_formats.XLSX()
        data = self.export_mixin.get_export_data(
            self.file_format, list(), request=self.mock_request
        )
        binary_dataset = tablib.import_set(data)
        self.assertEqual("teststr", binary_dataset.dict[0]["name"])

    def test_export_action_to_encoding(self):
        self.export_mixin.to_encoding = "utf-8"
        with mock.patch(
            "import_export.admin.ExportMixin.get_export_data"
        ) as mock_get_export_data:
            self.export_mixin.export_action(self.mock_request)
            encoding_kwarg = mock_get_export_data.call_args_list[0][1]["encoding"]
            self.assertEqual("utf-8", encoding_kwarg)

    @override_settings(IMPORT_EXPORT_SKIP_ADMIN_ACTION_EXPORT_UI=True)
    def test_export_admin_action_to_encoding(self):
        class TestExportActionMixin(ExportActionMixin):
            def get_export_filename(self, request, queryset, file_format):
                return "f"

        self.export_mixin = TestExportActionMixin()
        self.export_mixin.to_encoding = "utf-8"
        with mock.patch(
            "import_export.admin.ExportMixin.get_export_data"
        ) as mock_get_export_data:
            self.export_mixin.export_admin_action(self.mock_request, list())
            encoding_kwarg = mock_get_export_data.call_args_list[0][1]["encoding"]
            self.assertEqual("utf-8", encoding_kwarg)
