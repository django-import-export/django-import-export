import os
from io import StringIO
from unittest import mock
from unittest.mock import PropertyMock, patch

from core.admin import (
    AuthorAdmin,
    BookAdmin,
    CustomBookAdmin,
    EBookResource,
    ImportMixin,
)
from core.models import Author, Book, EBook, Parent
from core.tests.admin_integration.mixins import AdminTestMixin
from django.contrib.admin.models import DELETION, LogEntry
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.test import RequestFactory
from django.test.testcases import TestCase, TransactionTestCase
from django.test.utils import override_settings
from django.utils.translation import gettext_lazy as _

from import_export.admin import ExportMixin
from import_export.exceptions import FieldError
from import_export.formats import base_formats
from import_export.formats.base_formats import XLSX
from import_export.resources import ModelResource


class ImportTemplateTests(AdminTestMixin, TestCase):

    def test_import_export_template(self):
        response = self.client.get("/admin/core/book/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "admin/import_export/change_list_import_export.html"
        )
        self.assertTemplateUsed(response, "admin/change_list.html")
        self.assertTemplateUsed(response, "core/admin/change_list.html")
        self.assertContains(response, _("Import"))
        self.assertContains(response, _("Export"))
        self.assertContains(response, "Custom change list item")

    @patch("import_export.admin.logger")
    def test_issue_1521_change_list_template_as_property(self, mock_logger):
        # Test that a warning is logged when change_list_template is a property
        class TestImportCls(ImportMixin):
            @property
            def change_list_template(self):
                return ["x"]

        TestImportCls()
        mock_logger.warning.assert_called_once_with(
            "failed to assign change_list_template attribute"
        )

    def test_import_buttons_visible_without_add_permission(self):
        # When using ImportMixin, users should be able to see the import button
        # without add permission (to be consistent with ImportExportMixin)

        original = AuthorAdmin.has_add_permission
        AuthorAdmin.has_add_permission = lambda self, request: False
        response = self.client.get("/admin/core/author/")
        AuthorAdmin.has_add_permission = original

        self.assertContains(response, _("Import"))
        self.assertTemplateUsed(response, "admin/import_export/change_list.html")

    def test_import_export_buttons_visible_without_add_permission(self):
        # issue 38 - Export button not visible when no add permission
        original = BookAdmin.has_add_permission
        BookAdmin.has_add_permission = lambda self, request: False
        response = self.client.get(self.book_import_url)
        BookAdmin.has_add_permission = original

        self.assertContains(response, _("Export"))
        self.assertContains(response, _("Import"))

    @override_settings(DEBUG=True)
    def test_correct_scripts_declared_when_debug_is_true(self):
        # GET the import form
        response = self.client.get(self.book_import_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.admin_import_template)
        self.assertContains(response, 'form action=""')
        self.assertContains(
            response,
            '<script src="/static/admin/js/vendor/jquery/jquery.js">',
            count=1,
            html=True,
        )
        self.assertContains(
            response,
            '<script src="/static/admin/js/jquery.init.js">',
            count=1,
            html=True,
        )
        self.assertContains(
            response,
            '<script src="/static/import_export/guess_format.js">',
            count=1,
            html=True,
        )

    @override_settings(DEBUG=False)
    def test_correct_scripts_declared_when_debug_is_false(self):
        # GET the import form
        response = self.client.get(self.book_import_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.admin_import_template)
        self.assertContains(response, 'form action=""')
        self.assertContains(
            response,
            '<script src="/static/admin/js/vendor/jquery/jquery.min.js">',
            count=1,
            html=True,
        )
        self.assertContains(
            response,
            '<script src="/static/admin/js/jquery.init.js">',
            count=1,
            html=True,
        )
        self.assertContains(
            response,
            '<script src="/static/import_export/guess_format.js">',
            count=1,
            html=True,
        )

    def test_import_with_customized_forms(self):
        """Test if admin import works if forms are customized"""
        # We reuse import scheme from `test_import` to import books.csv.
        # We use customized BookAdmin (CustomBookAdmin) with modified import
        # form, which requires Author to be selected (from available authors).
        # Note that url is /admin/core/ebook/import (and not: ...book/import)!

        # We need at least a single author in the db to select from in the
        # admin import custom forms
        Author.objects.create(id=11, name="Test Author")

        # GET the import form
        response = self.client.get("/admin/core/ebook/import/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "admin/import_export/import.html")
        self.assertContains(response, 'form action=""')

        # POST the import form
        input_format = "0"
        filename = os.path.join(
            os.path.dirname(__file__),
            os.path.pardir,
            os.path.pardir,
            "exports",
            "books.csv",
        )
        with open(filename, "rb") as fobj:
            data = {"author": 11, "format": input_format, "import_file": fobj}
            response = self.client.post("/admin/core/ebook/import/", data)

        self.assertEqual(response.status_code, 200)
        self.assertIn("result", response.context)
        self.assertFalse(response.context["result"].has_errors())
        self.assertIn("confirm_form", response.context)
        confirm_form = response.context["confirm_form"]
        self.assertIsInstance(
            confirm_form,
            CustomBookAdmin(EBook, "ebook/import").get_confirm_form_class(None),
        )

        data = confirm_form.initial
        self.assertEqual(data["original_file_name"], "books.csv")
        response = self.client.post(
            "/admin/core/ebook/process_import/", data, follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            _(
                "Import finished: {} new, {} updated, {} deleted and {} skipped {}."
            ).format(1, 0, 0, 0, EBook._meta.verbose_name_plural),
        )

    def test_import_action_invalidates_data_sheet_with_no_headers_or_data(self):
        # GET the import form
        response = self.client.get(self.book_import_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.admin_import_template)
        self.assertContains(response, 'form action=""')

        response = self._do_import_post(
            self.book_import_url, "books-no-headers.csv", input_format=0
        )
        self.assertEqual(response.status_code, 200)
        target_msg = (
            "No valid data to import. Ensure your file "
            "has the correct headers or data for import."
        )
        self.assertFormError(response.context["form"], "import_file", target_msg)
