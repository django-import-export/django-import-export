import os
import warnings
from unittest import mock
from unittest.mock import MagicMock, patch

import django
from core.admin import AuthorAdmin, BookAdmin, CustomBookAdmin, ImportMixin
from core.models import Author, Book, EBook, Parent
from core.tests.admin_integration.mixins import AdminTestMixin
from core.tests.utils import ignore_widget_deprecation_warning
from django.contrib.admin.models import DELETION, LogEntry
from django.http import HttpRequest
from django.test.testcases import TestCase, TransactionTestCase
from django.test.utils import override_settings
from django.utils.translation import gettext_lazy as _

from import_export.admin import ExportMixin
from import_export.formats import base_formats


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
    @ignore_widget_deprecation_warning
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
    @ignore_widget_deprecation_warning
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

    @ignore_widget_deprecation_warning
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
    @ignore_widget_deprecation_warning
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

    @ignore_widget_deprecation_warning
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

    @ignore_widget_deprecation_warning
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

    @ignore_widget_deprecation_warning
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
    @ignore_widget_deprecation_warning
    def test_import_action_handles_TempFolderStorage_read(self):
        self._is_str_in_response("books.csv", "0")

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.TempFolderStorage"
    )
    @ignore_widget_deprecation_warning
    def test_import_action_handles_TempFolderStorage_read_mac(self):
        self._is_str_in_response("books-mac.csv", "0")

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.TempFolderStorage"
    )
    @ignore_widget_deprecation_warning
    def test_import_action_handles_TempFolderStorage_read_iso_8859_1(self):
        self._is_str_in_response("books-ISO-8859-1.csv", "0", "ISO-8859-1")

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.TempFolderStorage"
    )
    @ignore_widget_deprecation_warning
    def test_import_action_handles_TempFolderStorage_read_binary(self):
        self._is_str_in_response("books.xls", "1")

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.CacheStorage"
    )
    @ignore_widget_deprecation_warning
    def test_import_action_handles_CacheStorage_read(self):
        self._is_str_in_response("books.csv", "0")

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.CacheStorage"
    )
    @ignore_widget_deprecation_warning
    def test_import_action_handles_CacheStorage_read_mac(self):
        self._is_str_in_response("books-mac.csv", "0")

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.CacheStorage"
    )
    @ignore_widget_deprecation_warning
    def test_import_action_handles_CacheStorage_read_iso_8859_1(self):
        self._is_str_in_response("books-ISO-8859-1.csv", "0", "ISO-8859-1")

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.CacheStorage"
    )
    @ignore_widget_deprecation_warning
    def test_import_action_handles_CacheStorage_read_binary(self):
        self._is_str_in_response("books.xls", "1")

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.MediaStorage"
    )
    @ignore_widget_deprecation_warning
    def test_import_action_handles_MediaStorage_read(self):
        self._is_str_in_response("books.csv", "0")

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.MediaStorage"
    )
    @ignore_widget_deprecation_warning
    def test_import_action_handles_MediaStorage_read_mac(self):
        self._is_str_in_response("books-mac.csv", "0")

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.MediaStorage"
    )
    @ignore_widget_deprecation_warning
    def test_import_action_handles_MediaStorage_read_iso_8859_1(self):
        self._is_str_in_response("books-ISO-8859-1.csv", "0", "ISO-8859-1")

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.MediaStorage"
    )
    @ignore_widget_deprecation_warning
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
    @ignore_widget_deprecation_warning
    def test_import_action_handles_TempFolderStorage_read(self):
        self._is_str_in_response("books.csv", "0")

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.TempFolderStorage"
    )
    @ignore_widget_deprecation_warning
    def test_import_action_handles_TempFolderStorage_read_mac(self):
        self._is_str_in_response("books-mac.csv", "0")

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.TempFolderStorage"
    )
    @ignore_widget_deprecation_warning
    def test_import_action_handles_TempFolderStorage_read_iso_8859_1(self):
        self._is_str_in_response("books-ISO-8859-1.csv", "0", "ISO-8859-1")

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.TempFolderStorage"
    )
    @ignore_widget_deprecation_warning
    def test_import_action_handles_TempFolderStorage_read_binary(self):
        self._is_str_in_response("books.xls", "1")

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.CacheStorage"
    )
    @ignore_widget_deprecation_warning
    def test_import_action_handles_CacheStorage_read(self):
        self._is_str_in_response("books.csv", "0")

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.CacheStorage"
    )
    @ignore_widget_deprecation_warning
    def test_import_action_handles_CacheStorage_read_mac(self):
        self._is_str_in_response("books-mac.csv", "0")

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.CacheStorage"
    )
    @ignore_widget_deprecation_warning
    def test_import_action_handles_CacheStorage_read_iso_8859_1(self):
        self._is_str_in_response("books-ISO-8859-1.csv", "0", "ISO-8859-1")

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.CacheStorage"
    )
    @ignore_widget_deprecation_warning
    def test_import_action_handles_CacheStorage_read_binary(self):
        self._is_str_in_response("books.xls", "1")

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.MediaStorage"
    )
    @ignore_widget_deprecation_warning
    def test_import_action_handles_MediaStorage_read(self):
        self._is_str_in_response("books.csv", "0")

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.MediaStorage"
    )
    @ignore_widget_deprecation_warning
    def test_import_action_handles_MediaStorage_read_mac(self):
        self._is_str_in_response("books-mac.csv", "0")

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.MediaStorage"
    )
    @ignore_widget_deprecation_warning
    def test_import_action_handles_MediaStorage_read_iso_8859_1(self):
        self._is_str_in_response("books-ISO-8859-1.csv", "0", "ISO-8859-1")

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.MediaStorage"
    )
    @ignore_widget_deprecation_warning
    def test_import_action_handles_MediaStorage_read_binary(self):
        self._is_str_in_response("books.xls", "1")


@override_settings(IMPORT_EXPORT_SKIP_ADMIN_CONFIRM=True)
class TestImportSkipConfirm(AdminTestMixin, TransactionTestCase):
    fixtures = ["author"]

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

    @ignore_widget_deprecation_warning
    def test_import_action_create(self):
        self._is_str_in_response(
            "books.csv",
            "0",
            follow=True,
            str_in_response="Import finished, with 1 new and 0 updated books.",
        )
        self.assertEqual(1, Book.objects.count())

    @ignore_widget_deprecation_warning
    def test_import_action_invalid_date(self):
        # test that a row with an invalid date redirects to errors page
        index = self._get_input_format_index("csv")
        response = self._do_import_post(
            self.book_import_url, "books-invalid-date.csv", index
        )
        result = response.context["result"]
        # there should be a single invalid row
        self.assertEqual(1, len(result.invalid_rows))
        self.assertEqual(
            "Value could not be parsed using defined date formats.",
            result.invalid_rows[0].error.messages[0],
        )
        # no rows should be imported because we rollback on validation errors
        self.assertEqual(0, Book.objects.count())

    @ignore_widget_deprecation_warning
    def test_import_action_error_on_save(self):
        with mock.patch("core.models.Book.save") as mock_save:
            mock_save.side_effect = ValueError("some unknown error")
            response = self._do_import_post(self.book_import_url, "books.csv")
        self.assertIn("some unknown error", str(response.content))

    @override_settings(IMPORT_EXPORT_USE_TRANSACTIONS=True)
    def test_import_transaction_enabled_validation_error(self):
        # with transactions enabled, a validation error should cause the entire
        # import to be rolled back
        self._do_import_post(self.book_import_url, "books-invalid-date.csv")
        self.assertEqual(0, Book.objects.count())

    @override_settings(IMPORT_EXPORT_USE_TRANSACTIONS=False)
    @ignore_widget_deprecation_warning
    def test_import_transaction_disabled_validation_error(self):
        # with transactions disabled, a validation error should not cause the entire
        # import to fail
        self._do_import_post(self.book_import_url, "books-invalid-date.csv")
        self.assertEqual(1, Book.objects.count())

    @override_settings(IMPORT_EXPORT_USE_TRANSACTIONS=True)
    @ignore_widget_deprecation_warning
    def test_import_transaction_enabled_core_error(self):
        # test that if we send a file with multiple rows,
        # and transactions is enabled, a core error means that
        # no instances are persisted
        index = self._get_input_format_index("json")
        with mock.patch("core.admin.BookResource.skip_row") as mock_skip:
            mock_skip.side_effect = [None, ValueError("some unknown error"), None]
            response = self._do_import_post(self.book_import_url, "books.json", index)
        self.assertIn("some unknown error", str(response.content))
        self.assertEqual(0, Book.objects.count())

    @override_settings(IMPORT_EXPORT_USE_TRANSACTIONS=False)
    @ignore_widget_deprecation_warning
    def test_import_transaction_disabled_core_error(self):
        # with transactions disabled, a core (db constraint) error should not cause the
        # entire import to fail
        index = self._get_input_format_index("json")
        with mock.patch("core.admin.BookResource.skip_row") as mock_skip:
            mock_skip.side_effect = [None, ValueError("some unknown error"), None]
            response = self._do_import_post(self.book_import_url, "books.json", index)
        self.assertIn("some unknown error", str(response.content))
        self.assertEqual(2, Book.objects.count())

    @ignore_widget_deprecation_warning
    def test_import_action_mac(self):
        self._is_str_in_response(
            "books-mac.csv",
            "0",
            follow=True,
            str_in_response="Import finished, with 1 new and 0 updated books.",
        )

    @ignore_widget_deprecation_warning
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

    @ignore_widget_deprecation_warning
    def test_import_action_binary(self):
        self._is_str_in_response(
            "books.xls",
            "1",
            follow=True,
            str_in_response="Import finished, with 1 new and 0 updated books.",
        )
