import os.path
import warnings
from datetime import datetime
from io import BytesIO
from unittest import mock
from unittest.mock import MagicMock, patch

import chardet
import django
import tablib
from core.admin import AuthorAdmin, BookAdmin, CustomBookAdmin, ImportMixin
from core.models import Author, Book, Category, EBook, Parent
from django.contrib.admin.models import DELETION, LogEntry
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest
from django.test.testcases import TestCase, TransactionTestCase
from django.test.utils import override_settings
from django.utils.translation import gettext_lazy as _
from openpyxl.reader.excel import load_workbook
from tablib import Dataset

from import_export import formats
from import_export.admin import (
    ExportActionMixin,
    ExportActionModelAdmin,
    ExportMixin,
    ImportExportActionModelAdmin,
)
from import_export.formats import base_formats
from import_export.formats.base_formats import DEFAULT_FORMATS
from import_export.tmp_storages import TempFolderStorage


class AdminTestMixin(object):
    category_change_url = "/admin/core/category/"
    book_import_url = "/admin/core/book/import/"
    book_process_import_url = "/admin/core/book/process_import/"
    legacybook_import_url = "/admin/core/legacybook/import/"
    legacybook_process_import_url = "/admin/core/legacybook/process_import/"
    child_import_url = "/admin/core/child/import/"
    child_process_import_url = "/admin/core/child/process_import/"

    def setUp(self):
        super().setUp()
        user = User.objects.create_user("admin", "admin@example.com", "password")
        user.is_staff = True
        user.is_superuser = True
        user.save()
        self.client.login(username="admin", password="password")

    def _do_import_post(
        self, url, filename, input_format=0, encoding=None, resource=None, follow=False
    ):
        input_format = input_format
        filename = os.path.join(
            os.path.dirname(__file__), os.path.pardir, "exports", filename
        )
        with open(filename, "rb") as f:
            data = {
                "input_format": str(input_format),
                "import_file": f,
            }
            if encoding:
                BookAdmin.from_encoding = encoding
            if resource:
                data.update({"resource": resource})
            response = self.client.post(url, data, follow=follow)
        return response

    def _assert_string_in_response(
        self,
        url,
        filename,
        input_format,
        encoding=None,
        str_in_response=None,
        follow=False,
        status_code=200,
    ):
        response = self._do_import_post(
            url, filename, input_format, encoding=encoding, follow=follow
        )
        self.assertEqual(response.status_code, status_code)
        self.assertIn("result", response.context)
        self.assertFalse(response.context["result"].has_errors())
        if str_in_response is not None:
            self.assertContains(response, str_in_response)

    def _get_input_format_index(self, format):
        for i, f in enumerate(DEFAULT_FORMATS):
            if f().get_title() == format:
                xlsx_index = i
                break
        else:
            raise Exception(
                "Unable to find %s format. DEFAULT_FORMATS: %r"
                % (format, DEFAULT_FORMATS)
            )
        return xlsx_index


class ImportAdminIntegrationTest(AdminTestMixin, TestCase):
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

    @override_settings(TEMPLATE_STRING_IF_INVALID="INVALID_VARIABLE")
    def test_import(self):
        # GET the import form
        response = self.client.get(self.book_import_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "admin/import_export/import.html")
        self.assertContains(response, 'form action=""')

        response = self._do_import_post(self.book_import_url, "books.csv")
        self.assertEqual(response.status_code, 200)
        self.assertIn("result", response.context)
        self.assertFalse(response.context["result"].has_errors())
        self.assertIn("confirm_form", response.context)
        confirm_form = response.context["confirm_form"]

        data = confirm_form.initial
        self.assertEqual(data["original_file_name"], "books.csv")
        response = self.client.post(self.book_process_import_url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            _("Import finished, with {} new and {} updated {}.").format(
                1, 0, Book._meta.verbose_name_plural
            ),
        )

    @override_settings(DEBUG=True)
    def test_correct_scripts_declared_when_debug_is_true(self):
        # GET the import form
        response = self.client.get(self.book_import_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "admin/import_export/import.html")
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
        self.assertTemplateUsed(response, "admin/import_export/import.html")
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

    @override_settings(TEMPLATE_STRING_IF_INVALID="INVALID_VARIABLE")
    def test_import_second_resource(self):
        Book.objects.create(id=1)

        # GET the import form
        response = self.client.get(self.book_import_url)
        self.assertContains(response, "Export/Import only book names")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "admin/import_export/import.html")
        self.assertContains(response, 'form action=""')

        response = self._do_import_post(self.book_import_url, "books.csv", resource=1)
        self.assertEqual(response.status_code, 200)
        self.assertIn("result", response.context)
        self.assertFalse(response.context["result"].has_errors())
        self.assertIn("confirm_form", response.context)
        confirm_form = response.context["confirm_form"]

        data = confirm_form.initial
        self.assertEqual(data["original_file_name"], "books.csv")
        response = self.client.post(self.book_process_import_url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            _("Import finished, with {} new and {} updated {}.").format(
                0, 1, Book._meta.verbose_name_plural
            ),
        )
        # Check, that we really use second resource - author_email didn't get imported
        self.assertEqual(Book.objects.get(id=1).author_email, "")

    def test_import_legacy_book(self):
        """
        This test exists solely to test import works correctly using the deprecated
        functions.
        This test can be removed when the deprecated code is removed.
        """
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        Book.objects.create(id=1)

        # GET the import form
        response = self.client.get(self.legacybook_import_url)
        self.assertContains(response, "Export/Import only book names")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "admin/import_export/import.html")
        self.assertContains(response, 'form action=""')

        response = self._do_import_post(
            self.legacybook_import_url, "books.csv", resource=1
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("result", response.context)
        self.assertFalse(response.context["result"].has_errors())
        self.assertIn("confirm_form", response.context)
        confirm_form = response.context["confirm_form"]

        data = confirm_form.initial
        self.assertEqual(data["original_file_name"], "books.csv")
        response = self.client.post(
            self.legacybook_process_import_url, data, follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, "Import finished, with 0 new and 1 updated legacy books."
        )

    def test_export_admin_action(self):
        with mock.patch(
            "core.admin.CategoryAdmin.export_admin_action"
        ) as mock_export_admin_action:
            response = self.client.post(
                self.category_change_url,
                {
                    "action": "export_admin_action",
                    "index": "0",
                    "selected_across": "0",
                    "_selected_action": "0",
                },
            )
            assert 200 <= response.status_code <= 399
            mock_export_admin_action.assert_called()

    def test_import_action_handles_UnicodeDecodeError_as_form_error(self):
        with mock.patch(
            "import_export.admin.TempFolderStorage.read"
        ) as mock_tmp_folder_storage:
            b_arr = b"\x00"
            mock_tmp_folder_storage.side_effect = UnicodeDecodeError(
                "codec", b_arr, 1, 2, "fail!"
            )
            response = self._do_import_post(self.book_import_url, "books.csv")
        self.assertEqual(response.status_code, 200)
        target_msg = (
            "'UnicodeDecodeError' encountered while trying to read file. "
            "Ensure you have chosen the correct format for the file."
        )
        # required for testing via tox
        # remove after django 5.0 released
        if django.VERSION >= (4, 0):
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=DeprecationWarning)
                try:
                    self.assertFormError(
                        response.context["form"], "import_file", target_msg
                    )
                except TypeError:
                    self.assertFormError(response, "form", "import_file", target_msg)
        else:
            self.assertFormError(response, "form", "import_file", target_msg)

    def test_import_action_handles_ValueError_as_form_error(self):
        with mock.patch(
            "import_export.admin.TempFolderStorage.read"
        ) as mock_tmp_folder_storage:
            mock_tmp_folder_storage.side_effect = ValueError("some unknown error")
            response = self._do_import_post(self.book_import_url, "books.csv")
        self.assertEqual(response.status_code, 200)
        target_msg = (
            "'ValueError' encountered while trying to read file. "
            "Ensure you have chosen the correct format for the file."
        )

        # required for testing via tox
        # remove after django 5.0 released
        if django.VERSION >= (4, 0):
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=DeprecationWarning)
                try:
                    self.assertFormError(
                        response.context["form"], "import_file", target_msg
                    )
                except TypeError:
                    self.assertFormError(response, "form", "import_file", target_msg)
        else:
            self.assertFormError(response, "form", "import_file", target_msg)

    @override_settings(LANGUAGE_CODE="es")
    def test_import_action_handles_ValueError_as_form_error_with_translation(self):
        with mock.patch(
            "import_export.admin.TempFolderStorage.read"
        ) as mock_tmp_folder_storage:
            mock_tmp_folder_storage.side_effect = ValueError("some unknown error")
            response = self._do_import_post(self.book_import_url, "books.csv")
        self.assertEqual(response.status_code, 200)
        target_msg = (
            "Se encontró 'ValueError' mientras se intentaba leer el archivo. "
            "Asegúrese que seleccionó el formato correcto para el archivo."
        )

        # required for testing via tox
        # remove after django 5.0 released
        if django.VERSION >= (4, 0):
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=DeprecationWarning)
                try:
                    self.assertFormError(
                        response.context["form"], "import_file", target_msg
                    )
                except TypeError:
                    self.assertFormError(response, "form", "import_file", target_msg)
        else:
            self.assertFormError(response, "form", "import_file", target_msg)

    def test_delete_from_admin(self):
        # test delete from admin site (see #432)

        # create a book which can be deleted
        b = Book.objects.create(id=1)

        response = self._do_import_post(self.book_import_url, "books-for-delete.csv")
        self.assertEqual(response.status_code, 200)
        confirm_form = response.context["confirm_form"]
        data = confirm_form.initial
        response = self.client.post(self.book_process_import_url, data, follow=True)
        self.assertEqual(response.status_code, 200)

        # check the LogEntry was created as expected
        deleted_entry = LogEntry.objects.latest("id")
        self.assertEqual("delete through import_export", deleted_entry.change_message)
        self.assertEqual(DELETION, deleted_entry.action_flag)
        self.assertEqual(b.id, int(deleted_entry.object_id))
        self.assertEqual("", deleted_entry.object_repr)

    @override_settings(TEMPLATE_STRING_IF_INVALID="INVALID_VARIABLE")
    def test_import_mac(self):
        # GET the import form
        response = self.client.get(self.book_import_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "admin/import_export/import.html")
        self.assertContains(response, 'form action=""')

        response = self._do_import_post(self.book_import_url, "books-mac.csv")
        self.assertEqual(response.status_code, 200)
        self.assertIn("result", response.context)
        self.assertFalse(response.context["result"].has_errors())
        self.assertIn("confirm_form", response.context)
        confirm_form = response.context["confirm_form"]

        data = confirm_form.initial
        self.assertEqual(data["original_file_name"], "books-mac.csv")
        response = self.client.post(self.book_process_import_url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            _("Import finished, with {} new and {} updated {}.").format(
                1, 0, Book._meta.verbose_name_plural
            ),
        )

    def test_import_export_buttons_visible_without_add_permission(self):
        # issue 38 - Export button not visible when no add permission
        original = BookAdmin.has_add_permission
        BookAdmin.has_add_permission = lambda self, request: False
        response = self.client.get("/admin/core/book/")
        BookAdmin.has_add_permission = original

        self.assertContains(response, _("Export"))
        self.assertContains(response, _("Import"))

    def test_import_buttons_visible_without_add_permission(self):
        # When using ImportMixin, users should be able to see the import button
        # without add permission (to be consistent with ImportExportMixin)

        original = AuthorAdmin.has_add_permission
        AuthorAdmin.has_add_permission = lambda self, request: False
        response = self.client.get("/admin/core/author/")
        AuthorAdmin.has_add_permission = original

        self.assertContains(response, _("Import"))
        self.assertTemplateUsed(response, "admin/import_export/change_list.html")

    def test_import_file_name_in_tempdir(self):
        # 65 - import_file_name form field can be use to access the filesystem
        import_file_name = os.path.join(
            os.path.dirname(__file__), os.path.pardir, "exports", "books.csv"
        )
        data = {
            "input_format": "0",
            "import_file_name": import_file_name,
            "original_file_name": "books.csv",
        }
        with self.assertRaises(FileNotFoundError):
            self.client.post(self.book_process_import_url, data)

    def test_csrf(self):
        response = self.client.get(self.book_process_import_url)
        self.assertEqual(response.status_code, 405)

    def test_import_log_entry(self):
        response = self._do_import_post(self.book_import_url, "books.csv")

        self.assertEqual(response.status_code, 200)
        confirm_form = response.context["confirm_form"]
        data = confirm_form.initial
        response = self.client.post(self.book_process_import_url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        book = LogEntry.objects.latest("id")
        self.assertEqual(book.object_repr, "Some book")
        self.assertEqual(book.object_id, str(1))

    def test_import_log_entry_with_fk(self):
        Parent.objects.create(id=1234, name="Some Parent")
        response = self._do_import_post(self.child_import_url, "child.csv")
        self.assertEqual(response.status_code, 200)
        confirm_form = response.context["confirm_form"]
        data = confirm_form.initial
        response = self.client.post(
            "/admin/core/child/process_import/", data, follow=True
        )
        self.assertEqual(response.status_code, 200)
        child = LogEntry.objects.latest("id")
        self.assertEqual(child.object_repr, "Some - child of Some Parent")
        self.assertEqual(child.object_id, str(1))

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
            os.path.dirname(__file__), os.path.pardir, "exports", "books.csv"
        )
        with open(filename, "rb") as fobj:
            data = {"author": 11, "input_format": input_format, "import_file": fobj}
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
            _("Import finished, with {} new and {} updated {}.").format(
                1, 0, EBook._meta.verbose_name_plural
            ),
        )

    @mock.patch("core.admin.BookAdmin.get_import_form_class")
    def test_deprecated_importform_new_api_raises_warning(self, mock_get_import_form):
        class DjangoImportForm(django.forms.Form):
            def __init__(self, import_formats, *args, **kwargs):
                super().__init__(*args, **kwargs)

        mock_get_import_form.return_value = DjangoImportForm

        with self.assertWarnsRegex(
            DeprecationWarning,
            r"^The ImportForm class must inherit from ImportExportFormBase, "
            r"this is needed for multiple resource classes to work properly. $",
        ):
            # GET the import form
            response = self.client.get(self.book_import_url)
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, "admin/import_export/import.html")
            self.assertContains(response, 'form action=""')

    @mock.patch("core.admin.BookAdmin.get_import_form_class")
    @mock.patch("core.admin.BookAdmin.get_form_kwargs")
    def test_deprecated_importform_raises_warning(
        self, mock_get_form_kwargs, mock_get_import_form
    ):
        class DjangoImportForm(django.forms.Form):
            def __init__(self, import_formats, *args, **kwargs):
                super().__init__(*args, **kwargs)

        mock_get_form_kwargs.is_original = False
        mock_get_import_form.return_value = DjangoImportForm

        with self.assertWarnsRegex(
            DeprecationWarning,
            r"^The ImportForm class must inherit from ImportExportFormBase, "
            r"this is needed for multiple resource classes to work properly. $",
        ):
            # GET the import form
            response = self.client.get(self.book_import_url)
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, "admin/import_export/import.html")
            self.assertContains(response, 'form action=""')

    def test_get_skip_admin_log_attribute(self):
        m = ImportMixin()
        m.skip_admin_log = True
        self.assertTrue(m.get_skip_admin_log())

    def test_get_tmp_storage_class_attribute(self):
        """Mock dynamically loading a class defined by an attribute"""
        target = "SomeClass"
        m = ImportMixin()
        m.tmp_storage_class = "tmpClass"
        with mock.patch("import_export.admin.import_string") as mock_import_string:
            mock_import_string.return_value = target
            self.assertEqual(target, m.get_tmp_storage_class())

    def test_get_import_data_kwargs_with_form_kwarg(self):
        """
        Test that if a the method is called with a 'form' kwarg,
        then it is removed and the updated dict is returned
        """
        request = MagicMock(spec=HttpRequest)
        m = ImportMixin()
        kw = {"a": 1, "form": "some_form"}
        target = {"a": 1}
        self.assertEqual(target, m.get_import_data_kwargs(request, **kw))

    def test_get_import_data_kwargs_with_no_form_kwarg_returns_empty_dict(self):
        """
        Test that if the method is called with no 'form' kwarg,
        then an empty dict is returned
        """
        request = MagicMock(spec=HttpRequest)
        m = ImportMixin()
        kw = {
            "a": 1,
        }
        target = {}
        self.assertEqual(target, m.get_import_data_kwargs(request, **kw))

    def test_get_context_data_returns_empty_dict(self):
        m = ExportMixin()
        self.assertEqual(dict(), m.get_context_data())

    def test_media_attribute(self):
        """
        Test that the 'media' attribute of the ModelAdmin class is overridden to include
        the project-specific js file.
        """
        mock_model = mock.MagicMock()
        mock_site = mock.MagicMock()

        class TestExportActionModelAdmin(ExportActionModelAdmin):
            def __init__(self):
                super().__init__(mock_model, mock_site)

        m = TestExportActionModelAdmin()
        target_media = m.media
        self.assertEqual("import_export/action_formats.js", target_media._js[-1])

    @patch("import_export.admin.logger")
    def test_issue_1521_change_list_template_as_property(self, mock_logger):
        class TestImportCls(ImportMixin):
            @property
            def change_list_template(self):
                return ["x"]

        TestImportCls()
        mock_logger.warning.assert_called_once_with(
            "failed to assign change_list_template attribute"
        )

    @override_settings(IMPORT_FORMATS=[base_formats.XLSX, base_formats.XLS])
    def test_import_admin_uses_import_format_settings(self):
        """
        Test that import form only avails the formats provided by the
        IMPORT_FORMATS setting
        """
        request = self.client.get(self.book_import_url).wsgi_request
        mock_site = mock.MagicMock()
        import_form = BookAdmin(Book, mock_site).create_import_form(request)

        items = list(import_form.fields.items())
        file_format = items[len(items) - 1][1]
        choices = file_format.choices

        self.assertEqual(len(choices), 3)
        self.assertEqual(choices[0][1], "---")
        self.assertEqual(choices[1][1], "xlsx")
        self.assertEqual(choices[2][1], "xls")


class ExportAdminIntegrationTest(AdminTestMixin, TestCase):
    def test_export_displays_resources_fields(self):
        response = self.client.get("/admin/core/book/export/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["fields_list"],
            [
                (
                    "BookResource",
                    [
                        "id",
                        "name",
                        "author",
                        "author_email",
                        "imported",
                        "published",
                        "published_time",
                        "price",
                        "added",
                        "categories",
                    ],
                ),
                ("Export/Import only book names", ["id", "name"]),
            ],
        )

    def test_export(self):
        response = self.client.get("/admin/core/book/export/")
        self.assertEqual(response.status_code, 200)

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

    def test_export_legacy_resource(self):
        """
        This test exists solely to test import works correctly using the deprecated
        functions.
        This test can be removed when the deprecated code is removed.
        """
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        response = self.client.get("/admin/core/legacybook/export/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Export/Import only book names")

        data = {
            "file_format": "0",
            "resource": 1,
        }
        date_str = datetime.now().strftime("%Y-%m-%d")
        response = self.client.post("/admin/core/legacybook/export/", data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.has_header("Content-Disposition"))
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertEqual(
            response["Content-Disposition"],
            'attachment; filename="LegacyBook-{}.csv"'.format(date_str),
        )
        self.assertEqual(b"id,name\r\n", response.content)

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
    @patch("import_export.mixins.logger")
    def test_export_escape_formulae(self, mock_logger):
        Book.objects.create(id=1, name="=SUM(1+1)")
        Book.objects.create(id=2, name="<script>alert(1)</script>")
        response = self.client.get("/admin/core/book/export/")
        self.assertEqual(response.status_code, 200)

        xlsx_index = self._get_input_format_index("xlsx")
        data = {"file_format": str(xlsx_index)}
        response = self.client.post("/admin/core/book/export/", data)
        self.assertEqual(response.status_code, 200)
        content = response.content
        # #1698 temporary catch for deprecation warning in openpyxl
        # this catch block must be removed when openpyxl updated
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            wb = load_workbook(filename=BytesIO(content))
        self.assertEqual("<script>alert(1)</script>", wb.active["B2"].value)
        self.assertEqual("SUM(1+1)", wb.active["B3"].value)

        mock_logger.debug.assert_called_once_with(
            "IMPORT_EXPORT_ESCAPE_FORMULAE_ON_EXPORT is enabled"
        )

    @override_settings(IMPORT_EXPORT_ESCAPE_HTML_ON_EXPORT=True)
    def test_export_escape_html_deprecation_warning(self):
        response = self.client.get("/admin/core/book/export/")
        self.assertEqual(response.status_code, 200)

        xlsx_index = self._get_input_format_index("xlsx")
        data = {"file_format": str(xlsx_index)}
        with self.assertWarnsRegex(
            DeprecationWarning,
            r"IMPORT_EXPORT_ESCAPE_HTML_ON_EXPORT is deprecated "
            "and will be removed in a future release.",
        ):
            self.client.post("/admin/core/book/export/", data)


class FilteredExportAdminIntegrationTest(AdminTestMixin, TestCase):
    fixtures = ["category", "book", "author"]

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


class ConfirmImportEncodingTest(AdminTestMixin, TestCase):
    """Test handling 'confirm import' step using different file encodings
    and storage types.
    """

    def _is_str_in_response(self, filename, input_format, encoding=None):
        super()._assert_string_in_response(
            self.book_import_url,
            filename,
            input_format,
            encoding=encoding,
            str_in_response="test@example.com",
        )

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.TempFolderStorage"
    )
    def test_import_action_handles_TempFolderStorage_read(self):
        self._is_str_in_response("books.csv", "0")

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.TempFolderStorage"
    )
    def test_import_action_handles_TempFolderStorage_read_mac(self):
        self._is_str_in_response("books-mac.csv", "0")

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.TempFolderStorage"
    )
    def test_import_action_handles_TempFolderStorage_read_iso_8859_1(self):
        self._is_str_in_response("books-ISO-8859-1.csv", "0", "ISO-8859-1")

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.TempFolderStorage"
    )
    def test_import_action_handles_TempFolderStorage_read_binary(self):
        self._is_str_in_response("books.xls", "1")

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.CacheStorage"
    )
    def test_import_action_handles_CacheStorage_read(self):
        self._is_str_in_response("books.csv", "0")

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.CacheStorage"
    )
    def test_import_action_handles_CacheStorage_read_mac(self):
        self._is_str_in_response("books-mac.csv", "0")

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.CacheStorage"
    )
    def test_import_action_handles_CacheStorage_read_iso_8859_1(self):
        self._is_str_in_response("books-ISO-8859-1.csv", "0", "ISO-8859-1")

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.CacheStorage"
    )
    def test_import_action_handles_CacheStorage_read_binary(self):
        self._is_str_in_response("books.xls", "1")

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.MediaStorage"
    )
    def test_import_action_handles_MediaStorage_read(self):
        self._is_str_in_response("books.csv", "0")

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.MediaStorage"
    )
    def test_import_action_handles_MediaStorage_read_mac(self):
        self._is_str_in_response("books-mac.csv", "0")

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.MediaStorage"
    )
    def test_import_action_handles_MediaStorage_read_iso_8859_1(self):
        self._is_str_in_response("books-ISO-8859-1.csv", "0", "ISO-8859-1")

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.MediaStorage"
    )
    def test_import_action_handles_MediaStorage_read_binary(self):
        self._is_str_in_response("books.xls", "1")


class CompleteImportEncodingTest(AdminTestMixin, TestCase):
    """Test handling 'complete import' step using different file encodings
    and storage types.
    """

    def _is_str_in_response(self, filename, input_format, encoding=None):
        response = self._do_import_post(
            self.book_import_url, filename, input_format, encoding=encoding
        )
        confirm_form = response.context["confirm_form"]
        data = confirm_form.initial
        response = self.client.post(self.book_process_import_url, data, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, "Import finished, with 1 new and 0 updated books."
        )

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.TempFolderStorage"
    )
    def test_import_action_handles_TempFolderStorage_read(self):
        self._is_str_in_response("books.csv", "0")

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.TempFolderStorage"
    )
    def test_import_action_handles_TempFolderStorage_read_mac(self):
        self._is_str_in_response("books-mac.csv", "0")

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.TempFolderStorage"
    )
    def test_import_action_handles_TempFolderStorage_read_iso_8859_1(self):
        self._is_str_in_response("books-ISO-8859-1.csv", "0", "ISO-8859-1")

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.TempFolderStorage"
    )
    def test_import_action_handles_TempFolderStorage_read_binary(self):
        self._is_str_in_response("books.xls", "1")

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.CacheStorage"
    )
    def test_import_action_handles_CacheStorage_read(self):
        self._is_str_in_response("books.csv", "0")

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.CacheStorage"
    )
    def test_import_action_handles_CacheStorage_read_mac(self):
        self._is_str_in_response("books-mac.csv", "0")

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.CacheStorage"
    )
    def test_import_action_handles_CacheStorage_read_iso_8859_1(self):
        self._is_str_in_response("books-ISO-8859-1.csv", "0", "ISO-8859-1")

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.CacheStorage"
    )
    def test_import_action_handles_CacheStorage_read_binary(self):
        self._is_str_in_response("books.xls", "1")

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.MediaStorage"
    )
    def test_import_action_handles_MediaStorage_read(self):
        self._is_str_in_response("books.csv", "0")

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.MediaStorage"
    )
    def test_import_action_handles_MediaStorage_read_mac(self):
        self._is_str_in_response("books-mac.csv", "0")

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.MediaStorage"
    )
    def test_import_action_handles_MediaStorage_read_iso_8859_1(self):
        self._is_str_in_response("books-ISO-8859-1.csv", "0", "ISO-8859-1")

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.MediaStorage"
    )
    def test_import_action_handles_MediaStorage_read_binary(self):
        self._is_str_in_response("books.xls", "1")


class TestImportExportActionModelAdmin(ImportExportActionModelAdmin):
    def __init__(self, mock_model, mock_site, error_instance):
        self.error_instance = error_instance
        super().__init__(mock_model, mock_site)

    def write_to_tmp_storage(self, import_file, input_format):
        mock_storage = MagicMock(spec=TempFolderStorage)

        mock_storage.read.side_effect = self.error_instance
        return mock_storage


class ExportActionAdminIntegrationTest(AdminTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.cat1 = Category.objects.create(name="Cat 1")
        self.cat2 = Category.objects.create(name="Cat 2")

    def test_export(self):
        data = {
            "action": ["export_admin_action"],
            "file_format": "0",
            "_selected_action": [str(self.cat1.id)],
        }
        response = self.client.post("/admin/core/category/", data)
        self.assertContains(response, self.cat1.name, status_code=200)
        self.assertNotContains(response, self.cat2.name, status_code=200)
        self.assertTrue(response.has_header("Content-Disposition"))
        date_str = datetime.now().strftime("%Y-%m-%d")
        self.assertEqual(
            response["Content-Disposition"],
            'attachment; filename="Category-{}.csv"'.format(date_str),
        )

    def test_export_no_format_selected(self):
        data = {
            "action": ["export_admin_action"],
            "_selected_action": [str(self.cat1.id)],
        }
        response = self.client.post("/admin/core/category/", data)
        self.assertEqual(response.status_code, 302)

    def test_get_export_data_raises_PermissionDenied_when_no_export_permission_assigned(
        self,
    ):
        request = MagicMock(spec=HttpRequest)

        class TestMixin(ExportMixin):
            model = Book

            def has_export_permission(self, request):
                return False

        m = TestMixin()
        with self.assertRaises(PermissionDenied):
            m.get_export_data("0", Book.objects.none(), request=request)

    def test_export_admin_action_one_formats(self):
        mock_model = mock.MagicMock()
        mock_site = mock.MagicMock()

        class TestCategoryAdmin(ExportActionModelAdmin):
            def __init__(self):
                super().__init__(mock_model, mock_site)

            export_formats = [base_formats.CSV]

        m = TestCategoryAdmin()
        action_form = m.action_form

        items = list(action_form.base_fields.items())
        file_format = items[len(items) - 1][1]
        choices = file_format.choices

        self.assertNotEqual(choices[0][0], "---")
        self.assertEqual(choices[0][1], "csv")

    def test_export_admin_action_formats(self):
        mock_model = mock.MagicMock()
        mock_site = mock.MagicMock()

        class TestCategoryAdmin(ExportActionModelAdmin):
            def __init__(self):
                super().__init__(mock_model, mock_site)

        class TestFormatsCategoryAdmin(ExportActionModelAdmin):
            def __init__(self):
                super().__init__(mock_model, mock_site)

            export_formats = [base_formats.CSV, base_formats.JSON]

        m = TestCategoryAdmin()
        action_form = m.action_form

        items = list(action_form.base_fields.items())
        file_format = items[len(items) - 1][1]
        choices = file_format.choices

        self.assertEqual(choices[0][1], "---")
        self.assertEqual(len(choices), 9)

        m = TestFormatsCategoryAdmin()
        action_form = m.action_form

        items = list(action_form.base_fields.items())
        file_format = items[len(items) - 1][1]
        choices = file_format.choices

        self.assertEqual(choices[0][1], "---")
        self.assertEqual(len(m.export_formats) + 1, len(choices))

        self.assertIn("csv", [c[1] for c in choices])
        self.assertIn("json", [c[1] for c in choices])

    @override_settings(EXPORT_FORMATS=[base_formats.XLSX, base_formats.CSV])
    def test_export_admin_action_uses_export_format_settings(self):
        """
        Test that export action only avails the formats provided by the
        EXPORT_FORMATS setting
        """
        mock_model = mock.MagicMock()
        mock_site = mock.MagicMock()

        class TestCategoryAdmin(ExportActionModelAdmin):
            def __init__(self):
                super().__init__(mock_model, mock_site)

        m = TestCategoryAdmin()
        action_form = m.action_form

        items = list(action_form.base_fields.items())
        file_format = items[len(items) - 1][1]
        choices = file_format.choices

        self.assertEqual(len(choices), 3)
        self.assertEqual(choices[0][1], "---")
        self.assertEqual(choices[1][1], "xlsx")
        self.assertEqual(choices[2][1], "csv")

    @override_settings(IMPORT_EXPORT_FORMATS=[base_formats.XLS, base_formats.CSV])
    def test_export_admin_action_uses_import_export_format_settings(self):
        """
        Test that export action only avails the formats provided by the
        IMPORT_EXPORT_FORMATS setting
        """
        mock_model = mock.MagicMock()
        mock_site = mock.MagicMock()

        class TestCategoryAdmin(ExportActionModelAdmin):
            def __init__(self):
                super().__init__(mock_model, mock_site)

        m = TestCategoryAdmin()
        action_form = m.action_form

        items = list(action_form.base_fields.items())
        file_format = items[len(items) - 1][1]
        choices = file_format.choices

        self.assertEqual(len(choices), 3)
        self.assertEqual(choices[0][1], "---")
        self.assertEqual(choices[1][1], "xls")
        self.assertEqual(choices[2][1], "csv")


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

    @mock.patch("import_export.admin.ImportForm")
    def test_export_action_to_encoding(self, mock_form):
        mock_form.is_valid.return_value = True
        self.export_mixin.to_encoding = "utf-8"
        with mock.patch(
            "import_export.admin.ExportMixin.get_export_data"
        ) as mock_get_export_data:
            self.export_mixin.export_action(self.mock_request)
            encoding_kwarg = mock_get_export_data.call_args_list[0][1]["encoding"]
            self.assertEqual("utf-8", encoding_kwarg)

    @mock.patch("import_export.admin.ImportForm")
    def test_export_admin_action_to_encoding(self, mock_form):
        class TestExportActionMixin(ExportActionMixin):
            def get_export_filename(self, request, queryset, file_format):
                return "f"

        self.mock_request.POST = {"file_format": "1"}

        self.export_mixin = TestExportActionMixin()
        self.export_mixin.to_encoding = "utf-8"
        mock_form.is_valid.return_value = True
        with mock.patch(
            "import_export.admin.ExportMixin.get_export_data"
        ) as mock_get_export_data:
            self.export_mixin.export_admin_action(self.mock_request, list())
            encoding_kwarg = mock_get_export_data.call_args_list[0][1]["encoding"]
            self.assertEqual("utf-8", encoding_kwarg)


class TestImportMixinDeprecationWarnings(TestCase):
    class TestMixin(ImportMixin):
        """
        TestMixin is a subclass which mimics a
        class which the user may have created
        """

        def get_import_form(self):
            return super().get_import_form()

        def get_confirm_import_form(self):
            return super().get_confirm_import_form()

        def get_form_kwargs(self, form_class, **kwargs):
            return super().get_form_kwargs(form_class, **kwargs)

    def setUp(self):
        super().setUp()
        self.import_mixin = ImportMixin()

    def test_get_import_form_warning(self):
        target_msg = (
            "ImportMixin.get_import_form() is deprecated and will be removed "
            "in a future release. "
            "Please use get_import_form_class() instead."
        )
        with self.assertWarns(DeprecationWarning) as w:
            self.import_mixin.get_import_form()
            self.assertEqual(target_msg, str(w.warnings[0].message))

    def test_get_confirm_import_form_warning(self):
        target_msg = (
            "ImportMixin.get_confirm_import_form() is deprecated and will be removed "
            "in a future release. "
            "Please use get_confirm_form_class() instead."
        )
        with self.assertWarns(DeprecationWarning) as w:
            self.import_mixin.get_confirm_import_form()
            self.assertEqual(target_msg, str(w.warnings[0].message))

    def test_get_form_kwargs_warning(self):
        target_msg = (
            "ImportMixin.get_form_kwargs() is deprecated and will be removed in a "
            "future release. "
            "Please use get_import_form_kwargs() or get_confirm_form_kwargs() instead."
        )
        with self.assertWarns(DeprecationWarning) as w:
            self.import_mixin.get_form_kwargs(None)
            self.assertEqual(target_msg, str(w.warnings[0].message))

    def test_get_import_form_class_warning(self):
        self.import_mixin = self.TestMixin()
        target_msg = (
            "ImportMixin.get_import_form() is deprecated and will be removed in a "
            "future release. "
            "Please use the new 'import_form_class' attribute to specify a custom form "
            "class, "
            "or override the get_import_form_class() method if your requirements are "
            "more complex."
        )
        with self.assertWarns(DeprecationWarning) as w:
            self.import_mixin.get_import_form_class(None)
            self.assertEqual(target_msg, str(w.warnings[0].message))

    def test_get_confirm_form_class_warning(self):
        self.import_mixin = self.TestMixin()
        target_msg = (
            "ImportMixin.get_confirm_import_form() is deprecated and will be removed "
            "in a future release. "
            "Please use the new 'confirm_form_class' attribute to specify a custom "
            "form class, "
            "or override the get_confirm_form_class() method if your requirements "
            "are more complex."
        )
        with self.assertWarns(DeprecationWarning) as w:
            self.import_mixin.get_confirm_form_class(None)
            self.assertEqual(target_msg, str(w.warnings[0].message))


class TestExportMixinDeprecationWarnings(TestCase):
    class TestMixin(ExportMixin):
        """
        TestMixin is a subclass which mimics a
        class which the user may have created
        """

        def get_export_form(self):
            return super().get_export_form()

    def setUp(self):
        super().setUp()
        self.export_mixin = self.TestMixin()

    def test_get_export_form_warning(self):
        target_msg = (
            "ExportMixin.get_export_form() is deprecated and will "
            "be removed in a future release. Please use the new "
            "'export_form_class' attribute to specify a custom form "
            "class, or override the get_export_form_class() method if "
            "your requirements are more complex."
        )
        with self.assertWarns(DeprecationWarning) as w:
            self.export_mixin.get_export_form()
            self.assertEqual(target_msg, str(w.warnings[0].message))


@override_settings(IMPORT_EXPORT_SKIP_ADMIN_CONFIRM=True)
class TestImportSkipConfirm(AdminTestMixin, TransactionTestCase):
    def _is_str_in_response(
        self,
        filename,
        input_format,
        encoding=None,
        str_in_response=None,
        follow=False,
        status_code=200,
    ):
        response = self._do_import_post(
            self.book_import_url,
            filename,
            input_format,
            encoding=encoding,
            follow=follow,
        )
        self.assertEqual(response.status_code, status_code)
        if str_in_response is not None:
            self.assertContains(response, str_in_response)

    def _is_regex_in_response(
        self,
        filename,
        input_format,
        encoding=None,
        regex_in_response=None,
        follow=False,
        status_code=200,
    ):
        response = self._do_import_post(
            self.book_import_url,
            filename,
            input_format,
            encoding=encoding,
            follow=follow,
        )
        self.assertEqual(response.status_code, status_code)
        if regex_in_response is not None:
            self.assertRegex(str(response.content), regex_in_response)

    def test_import_action_create(self):
        self._is_str_in_response(
            "books.csv",
            "0",
            follow=True,
            str_in_response="Import finished, with 1 new and 0 updated books.",
        )
        self.assertEqual(1, Book.objects.count())

    def test_import_action_invalid_date(self):
        # test that a row with an invalid date redirects to errors page
        response = self._do_import_post(
            self.book_import_url, "books-invalid-date.csv", "0"
        )
        result = response.context["result"]
        # there should be a single invalid row
        self.assertEqual(1, len(result.invalid_rows))
        self.assertEqual(
            "Enter a valid date.", result.invalid_rows[0].error.messages[0]
        )
        # no rows should be imported because we rollback on validation errors
        self.assertEqual(0, Book.objects.count())

    def test_import_action_empty_author_email(self):
        xlsx_index = self._get_input_format_index("xlsx")
        # sqlite / MySQL / Postgres have different error messages
        self._is_regex_in_response(
            "books-empty-author-email.xlsx",
            xlsx_index,
            follow=True,
            regex_in_response=r"(NOT NULL|null value in column|cannot be null)",
        )

    @override_settings(IMPORT_EXPORT_USE_TRANSACTIONS=True)
    def test_import_transaction_enabled_validation_error(self):
        # with transactions enabled, a validation error should cause the entire
        # import to be rolled back
        self._do_import_post(self.book_import_url, "books-invalid-date.csv")
        self.assertEqual(0, Book.objects.count())

    @override_settings(IMPORT_EXPORT_USE_TRANSACTIONS=False)
    def test_import_transaction_disabled_validation_error(self):
        # with transactions disabled, a validation error should not cause the entire
        # import to fail
        self._do_import_post(self.book_import_url, "books-invalid-date.csv")
        self.assertEqual(1, Book.objects.count())

    @override_settings(IMPORT_EXPORT_USE_TRANSACTIONS=True)
    def test_import_transaction_enabled_core_error(self):
        # with transactions enabled, a core error should cause the entire import to fail
        xlsx_index = self._get_input_format_index("xlsx")
        self._do_import_post(
            self.book_import_url, "books-empty-author-email.xlsx", xlsx_index
        )
        self.assertEqual(0, Book.objects.count())

    @override_settings(IMPORT_EXPORT_USE_TRANSACTIONS=False)
    def test_import_transaction_disabled_core_error(self):
        # with transactions disabled, a core (db contraint) error should not cause the
        # entire import to fail
        xlsx_index = self._get_input_format_index("xlsx")
        self._do_import_post(
            self.book_import_url, "books-empty-author-email.xlsx", xlsx_index
        )
        self.assertEqual(1, Book.objects.count())

    def test_import_action_mac(self):
        self._is_str_in_response(
            "books-mac.csv",
            "0",
            follow=True,
            str_in_response="Import finished, with 1 new and 0 updated books.",
        )

    def test_import_action_iso_8859_1(self):
        self._is_str_in_response(
            "books-ISO-8859-1.csv",
            "0",
            "ISO-8859-1",
            follow=True,
            str_in_response="Import finished, with 1 new and 0 updated books.",
        )

    def test_import_action_decode_error(self):
        # attempting to read a file with the incorrect encoding should raise an error
        self._is_regex_in_response(
            "books-ISO-8859-1.csv",
            "0",
            follow=True,
            encoding="utf-8-sig",
            regex_in_response=(
                ".*UnicodeDecodeError.* encountered " "while trying to read file"
            ),
        )

    def test_import_action_binary(self):
        self._is_str_in_response(
            "books.xls",
            "1",
            follow=True,
            str_in_response="Import finished, with 1 new and 0 updated books.",
        )
