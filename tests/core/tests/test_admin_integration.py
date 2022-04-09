import os.path
import warnings
from datetime import datetime
from unittest import mock
from unittest.mock import MagicMock

import chardet
import django
import tablib
from core.admin import (
    AuthorAdmin,
    BookAdmin,
    BookResource,
    CustomBookAdmin,
    ImportMixin,
)
from core.models import Author, Book, Category, EBook, Parent
from django.contrib.admin.models import DELETION, LogEntry
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpRequest
from django.test.testcases import TestCase
from django.test.utils import override_settings
from django.utils.translation import gettext_lazy as _
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


class ImportExportAdminIntegrationTest(TestCase):

    def setUp(self):
        user = User.objects.create_user('admin', 'admin@example.com',
                                        'password')
        user.is_staff = True
        user.is_superuser = True
        user.save()
        self.client.login(username='admin', password='password')

    def test_import_export_template(self):
        response = self.client.get('/admin/core/book/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response,
                'admin/import_export/change_list_import_export.html')
        self.assertContains(response, _('Import'))
        self.assertContains(response, _('Export'))

    @override_settings(TEMPLATE_STRING_IF_INVALID='INVALID_VARIABLE')
    def test_import(self):
        # GET the import form
        response = self.client.get('/admin/core/book/import/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/import_export/import.html')
        self.assertContains(response, 'form action=""')

        # POST the import form
        input_format = '0'
        filename = os.path.join(
            os.path.dirname(__file__),
            os.path.pardir,
            'exports',
            'books.csv')
        with open(filename, "rb") as f:
            data = {
                'input_format': input_format,
                'import_file': f,
            }
            response = self.client.post('/admin/core/book/import/', data)
        self.assertEqual(response.status_code, 200)
        self.assertIn('result', response.context)
        self.assertFalse(response.context['result'].has_errors())
        self.assertIn('confirm_form', response.context)
        confirm_form = response.context['confirm_form']

        data = confirm_form.initial
        self.assertEqual(data['original_file_name'], 'books.csv')
        response = self.client.post('/admin/core/book/process_import/', data,
                                    follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response,
            _('Import finished, with {} new and {} updated {}.').format(
                1, 0, Book._meta.verbose_name_plural)
        )

    @override_settings(TEMPLATE_STRING_IF_INVALID='INVALID_VARIABLE')
    def test_import_second_resource(self):
        Book.objects.create(id=1)

        # GET the import form
        response = self.client.get('/admin/core/book/import/')
        self.assertContains(response, "Export/Import only book names")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/import_export/import.html')
        self.assertContains(response, 'form action=""')

        # POST the import form
        input_format = '0'
        filename = os.path.join(
            os.path.dirname(__file__),
            os.path.pardir,
            'exports',
            'books.csv')
        with open(filename, "rb") as f:
            data = {
                'input_format': input_format,
                'import_file': f,
                'resource': 1,
            }
            response = self.client.post('/admin/core/book/import/', data)
        self.assertEqual(response.status_code, 200)
        self.assertIn('result', response.context)
        with open("response.html", "wb") as f:
            f.write(response.content)
        self.assertFalse(response.context['result'].has_errors())
        self.assertIn('confirm_form', response.context)
        confirm_form = response.context['confirm_form']

        data = confirm_form.initial
        self.assertEqual(data['original_file_name'], 'books.csv')
        response = self.client.post('/admin/core/book/process_import/', data,
                                    follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response,
            _('Import finished, with {} new and {} updated {}.').format(
                0, 1, Book._meta.verbose_name_plural)
        )
        # Check, that we really use second resource - author_email didn't get imported
        self.assertEqual(Book.objects.get(id=1).author_email, "")

    def test_import_action_handles_UnicodeDecodeError_as_form_error(self):
        # POST the import form
        input_format = '0'
        filename = os.path.join(
            os.path.dirname(__file__),
            os.path.pardir,
            'exports',
            'books.csv')
        with open(filename, "rb") as f:
            data = {
                'input_format': input_format,
                'import_file': f,
            }
            with mock.patch("import_export.admin.TempFolderStorage.read") as mock_tmp_folder_storage:
                b_arr = b'\x00'
                mock_tmp_folder_storage.side_effect = UnicodeDecodeError('codec', b_arr, 1, 2, 'fail!')
                response = self.client.post('/admin/core/book/import/', data)
        self.assertEqual(response.status_code, 200)
        target_msg = (
            '\'UnicodeDecodeError\' encountered while trying to read file. '
            'Ensure you have chosen the correct format for the file. '
            '\'codec\' codec can\'t decode bytes in position 1-1: fail!'
        )
        # required for testing via tox
        # remove after django 5.0 released
        if django.VERSION >= (4, 0):
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=DeprecationWarning)
                try:
                    self.assertFormError(response.context['form'], 'import_file', target_msg)
                except TypeError:
                    self.assertFormError(response, 'form', 'import_file', target_msg)
        else:
            self.assertFormError(response, 'form', 'import_file', target_msg)

    def test_import_action_handles_ValueError_as_form_error(self):
        # POST the import form
        input_format = '0'
        filename = os.path.join(
            os.path.dirname(__file__),
            os.path.pardir,
            'exports',
            'books.csv')
        with open(filename, "rb") as f:
            data = {
                'input_format': input_format,
                'import_file': f,
            }
            with mock.patch("import_export.admin.TempFolderStorage.read") as mock_tmp_folder_storage:
                mock_tmp_folder_storage.side_effect = ValueError('some unknown error')
                response = self.client.post('/admin/core/book/import/', data)
        self.assertEqual(response.status_code, 200)
        target_msg = (
            '\'ValueError\' encountered while trying to read file. '
            'Ensure you have chosen the correct format for the file. '
            'some unknown error'
        )

        # required for testing via tox
        # remove after django 5.0 released
        if django.VERSION >= (4, 0):
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=DeprecationWarning)
                try:
                    self.assertFormError(response.context['form'], 'import_file', target_msg)
                except TypeError:
                    self.assertFormError(response, 'form', 'import_file', target_msg)
        else:
            self.assertFormError(response, 'form', 'import_file', target_msg)

    def assert_string_in_response(self, filename, input_format, encoding=None):
        input_format = input_format
        filename = os.path.join(
            os.path.dirname(__file__),
            os.path.pardir,
            'exports',
            filename)
        with open(filename, "rb") as f:
            data = {
                'input_format': input_format,
                'import_file': f,
            }
            if encoding:
                BookAdmin.from_encoding = encoding
            response = self.client.post('/admin/core/book/import/', data)
        self.assertEqual(response.status_code, 200)
        self.assertIn('result', response.context)
        self.assertFalse(response.context['result'].has_errors())
        self.assertContains(response, 'test@example.com')

    @override_settings(IMPORT_EXPORT_TMP_STORAGE_CLASS='import_export.tmp_storages.TempFolderStorage')
    def test_import_action_handles_TempFolderStorage_read(self):
        self.assert_string_in_response('books.csv', '0')

    @override_settings(IMPORT_EXPORT_TMP_STORAGE_CLASS='import_export.tmp_storages.TempFolderStorage')
    def test_import_action_handles_TempFolderStorage_read_iso_8859_1(self):
        self.assert_string_in_response('books-ISO-8859-1.csv', '0', 'ISO-8859-1')

    @override_settings(IMPORT_EXPORT_TMP_STORAGE_CLASS='import_export.tmp_storages.CacheStorage')
    def test_import_action_handles_CacheStorage_read(self):
        self.assert_string_in_response('books.csv', '0')

    @override_settings(IMPORT_EXPORT_TMP_STORAGE_CLASS='import_export.tmp_storages.CacheStorage')
    def test_import_action_handles_CacheStorage_read_iso_8859_1(self):
        self.assert_string_in_response('books-ISO-8859-1.csv', '0', 'ISO-8859-1')

    @override_settings(IMPORT_EXPORT_TMP_STORAGE_CLASS='import_export.tmp_storages.CacheStorage')
    def test_import_action_handles_CacheStorage_read_binary(self):
        self.assert_string_in_response('books.xls', '1')

    @override_settings(IMPORT_EXPORT_TMP_STORAGE_CLASS='import_export.tmp_storages.MediaStorage')
    def test_import_action_handles_MediaStorage_read(self):
        self.assert_string_in_response('books.csv', '0')

    @override_settings(IMPORT_EXPORT_TMP_STORAGE_CLASS='import_export.tmp_storages.MediaStorage')
    def test_import_action_handles_MediaStorage_read_iso_8859_1(self):
        self.assert_string_in_response('books-ISO-8859-1.csv', '0', 'ISO-8859-1')

    @override_settings(IMPORT_EXPORT_TMP_STORAGE_CLASS='import_export.tmp_storages.MediaStorage')
    def test_import_action_handles_MediaStorage_read_binary(self):
        self.assert_string_in_response('books.xls', '1')

    def test_delete_from_admin(self):
        # test delete from admin site (see #432)

        # create a book which can be deleted
        b = Book.objects.create(id=1)

        input_format = '0'
        filename = os.path.join(
            os.path.dirname(__file__),
            os.path.pardir,
            'exports',
            'books-for-delete.csv')
        with open(filename, "rb") as f:
            data = {
                'input_format': input_format,
                'import_file': f,
            }
            response = self.client.post('/admin/core/book/import/', data)
        self.assertEqual(response.status_code, 200)
        confirm_form = response.context['confirm_form']
        data = confirm_form.initial
        response = self.client.post('/admin/core/book/process_import/', data,
                                    follow=True)
        self.assertEqual(response.status_code, 200)

        # check the LogEntry was created as expected
        deleted_entry = LogEntry.objects.latest('id')
        self.assertEqual("delete through import_export", deleted_entry.change_message)
        self.assertEqual(DELETION, deleted_entry.action_flag)
        self.assertEqual(b.id, int(deleted_entry.object_id))
        self.assertEqual("", deleted_entry.object_repr)

    @override_settings(TEMPLATE_STRING_IF_INVALID='INVALID_VARIABLE')
    def test_import_mac(self):
        # GET the import form
        response = self.client.get('/admin/core/book/import/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/import_export/import.html')
        self.assertContains(response, 'form action=""')

        # POST the import form
        input_format = '0'
        filename = os.path.join(
            os.path.dirname(__file__),
            os.path.pardir,
            'exports',
            'books-mac.csv')
        with open(filename, "rb") as f:
            data = {
                'input_format': input_format,
                'import_file': f,
            }
            response = self.client.post('/admin/core/book/import/', data)
        self.assertEqual(response.status_code, 200)
        self.assertIn('result', response.context)
        self.assertFalse(response.context['result'].has_errors())
        self.assertIn('confirm_form', response.context)
        confirm_form = response.context['confirm_form']

        data = confirm_form.initial
        self.assertEqual(data['original_file_name'], 'books-mac.csv')
        response = self.client.post('/admin/core/book/process_import/', data,
                                    follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response,
            _('Import finished, with {} new and {} updated {}.').format(
                1, 0, Book._meta.verbose_name_plural)
        )

    def test_export(self):
        response = self.client.get('/admin/core/book/export/')
        self.assertEqual(response.status_code, 200)

        data = {
            'file_format': '0',
            }
        date_str = datetime.now().strftime('%Y-%m-%d')
        response = self.client.post('/admin/core/book/export/', data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.has_header("Content-Disposition"))
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertEqual(
            response['Content-Disposition'],
            'attachment; filename="Book-{}.csv"'.format(date_str)
        )
        self.assertEqual(
            b"id,name,author,author_email,imported,published,"
            b"published_time,price,added,categories\r\n",
            response.content,
        )

    def test_export_second_resource(self):
        response = self.client.get('/admin/core/book/export/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Export/Import only book names")

        data = {
            'file_format': '0',
            'resource': 1,
            }
        date_str = datetime.now().strftime('%Y-%m-%d')
        response = self.client.post('/admin/core/book/export/', data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.has_header("Content-Disposition"))
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertEqual(
            response['Content-Disposition'],
            'attachment; filename="Book-{}.csv"'.format(date_str)
        )
        self.assertEqual(b"id,name\r\n", response.content)

    def test_returns_xlsx_export(self):
        response = self.client.get('/admin/core/book/export/')
        self.assertEqual(response.status_code, 200)

        for i, f in enumerate(DEFAULT_FORMATS):
            if f().get_title() == 'xlsx':
                xlsx_index = i
                break
        else:
            self.fail('Unable to find xlsx format. DEFAULT_FORMATS: %r' % DEFAULT_FORMATS)
        data = {'file_format': str(xlsx_index)}
        response = self.client.post('/admin/core/book/export/', data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.has_header("Content-Disposition"))
        self.assertEqual(response['Content-Type'],
                         'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    def test_import_export_buttons_visible_without_add_permission(self):
        # issue 38 - Export button not visible when no add permission
        original = BookAdmin.has_add_permission
        BookAdmin.has_add_permission = lambda self, request: False
        response = self.client.get('/admin/core/book/')
        BookAdmin.has_add_permission = original

        self.assertContains(response, _('Export'))
        self.assertContains(response, _('Import'))

    def test_import_buttons_visible_without_add_permission(self):
        # When using ImportMixin, users should be able to see the import button
        # without add permission (to be consistent with ImportExportMixin)

        original = AuthorAdmin.has_add_permission
        AuthorAdmin.has_add_permission = lambda self, request: False
        response = self.client.get('/admin/core/author/')
        AuthorAdmin.has_add_permission = original

        self.assertContains(response, _('Import'))
        self.assertTemplateUsed(response, 'admin/import_export/change_list.html')

    def test_import_file_name_in_tempdir(self):
        # 65 - import_file_name form field can be use to access the filesystem
        import_file_name = os.path.join(
            os.path.dirname(__file__),
            os.path.pardir,
            'exports',
            'books.csv')
        data = {
            'input_format': "0",
            'import_file_name': import_file_name,
            'original_file_name': 'books.csv'
        }
        with self.assertRaises(FileNotFoundError):
            self.client.post('/admin/core/book/process_import/', data)

    def test_csrf(self):
        response = self.client.get('/admin/core/book/process_import/')
        self.assertEqual(response.status_code, 405)

    def test_import_log_entry(self):
        input_format = '0'
        filename = os.path.join(
            os.path.dirname(__file__),
            os.path.pardir,
            'exports',
            'books.csv')
        with open(filename, "rb") as f:
            data = {
                'input_format': input_format,
                'import_file': f,
            }
            response = self.client.post('/admin/core/book/import/', data)
        self.assertEqual(response.status_code, 200)
        confirm_form = response.context['confirm_form']
        data = confirm_form.initial
        response = self.client.post('/admin/core/book/process_import/', data,
                                    follow=True)
        self.assertEqual(response.status_code, 200)
        book = LogEntry.objects.latest('id')
        self.assertEqual(book.object_repr, "Some book")
        self.assertEqual(book.object_id, str(1))

    def test_import_log_entry_with_fk(self):
        Parent.objects.create(id=1234, name='Some Parent')
        input_format = '0'
        filename = os.path.join(
            os.path.dirname(__file__),
            os.path.pardir,
            'exports',
            'child.csv')
        with open(filename, "rb") as f:
            data = {
                'input_format': input_format,
                'import_file': f,
            }
            response = self.client.post('/admin/core/child/import/', data)
        self.assertEqual(response.status_code, 200)
        confirm_form = response.context['confirm_form']
        data = confirm_form.initial
        response = self.client.post('/admin/core/child/process_import/', data,
                                    follow=True)
        self.assertEqual(response.status_code, 200)
        child = LogEntry.objects.latest('id')
        self.assertEqual(child.object_repr, 'Some - child of Some Parent')
        self.assertEqual(child.object_id, str(1))

    def test_logentry_creation_with_import_obj_exception(self):
        # from https://mail.python.org/pipermail/python-dev/2008-January/076194.html
        def monkeypatch_method(cls):
            def decorator(func):
                setattr(cls, func.__name__, func)
                return func
            return decorator

        # Cause an exception in import_row, but only after import is confirmed,
        # so a failure only occurs when ImportMixin.process_import is called.
        class R(BookResource):
            def import_obj(self, obj, data, dry_run, **kwargs):
                if dry_run:
                    super().import_obj(obj, data, dry_run, **kwargs)
                else:
                    raise Exception

        @monkeypatch_method(BookAdmin)
        def get_resource_classes(self):
            return [R]

        # Verify that when an exception occurs in import_row, when raise_errors is False,
        # the returned row result has a correct import_type value,
        # so generating log entries does not fail.
        @monkeypatch_method(BookAdmin)
        def process_dataset(self, dataset, confirm_form, request, *args, **kwargs):
            resource = self.get_import_resource_classes()[0](**self.get_import_resource_kwargs(request, *args, **kwargs))
            return resource.import_data(dataset,
                                        dry_run=False,
                                        raise_errors=False,
                                        file_name=confirm_form.cleaned_data['original_file_name'],
                                        user=request.user,
                                        **kwargs)

        dataset = Dataset(headers=["id","name","author_email"])
        dataset.append([1, "Test 1", "test@example.com"])
        input_format = '0'
        content = dataset.csv
        f = SimpleUploadedFile("data.csv", content.encode(), content_type="text/csv")
        data = {
            "input_format": input_format,
            "import_file": f,
        }
        response = self.client.post('/admin/core/book/import/', data)
        self.assertEqual(response.status_code, 200)
        confirm_form = response.context['confirm_form']
        data = confirm_form.initial
        response = self.client.post('/admin/core/book/process_import/', data,
                                    follow=True)
        self.assertEqual(response.status_code, 200)

    def test_import_with_customized_forms(self):
        """Test if admin import works if forms are customized"""
        # We reuse import scheme from `test_import` to import books.csv.
        # We use customized BookAdmin (CustomBookAdmin) with modified import
        # form, which requires Author to be selected (from available authors).
        # Note that url is /admin/core/ebook/import (and not: ...book/import)!

        # We need at least a single author in the db to select from in the
        # admin import custom forms
        Author.objects.create(id=11, name='Test Author')

        # GET the import form
        response = self.client.get('/admin/core/ebook/import/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/import_export/import.html')
        self.assertContains(response, 'form action=""')

        # POST the import form
        input_format = '0'
        filename = os.path.join(os.path.dirname(__file__),
                                os.path.pardir,
                                'exports',
                                'books.csv')
        with open(filename, "rb") as fobj:
            data = {'author': 11,
                    'input_format': input_format,
                    'import_file': fobj}
            response = self.client.post('/admin/core/ebook/import/', data)

        self.assertEqual(response.status_code, 200)
        self.assertIn('result', response.context)
        self.assertFalse(response.context['result'].has_errors())
        self.assertIn('confirm_form', response.context)
        confirm_form = response.context['confirm_form']
        self.assertIsInstance(confirm_form,
                              CustomBookAdmin(EBook, 'ebook/import')
                              .get_confirm_import_form())

        data = confirm_form.initial
        self.assertEqual(data['original_file_name'], 'books.csv')
        response = self.client.post('/admin/core/ebook/process_import/',
                                    data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            _('Import finished, with {} new and {} updated {}.').format(
                1, 0, EBook._meta.verbose_name_plural)
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
        kw = {
            "a": 1,
            "form": "some_form"
        }
        target = {
            "a": 1
        }
        self.assertEqual(target, m.get_import_data_kwargs(request, **kw))

    def test_get_import_data_kwargs_with_no_form_kwarg_returns_empty_dict(self):
        """
        Test that if a the method is called with no 'form' kwarg,
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
        self.assertEqual('import_export/action_formats.js', target_media._js[-1])


class ConfirmImportEncodingTest(TestCase):
    """Test handling 'confirm import' step using different file encodings
    and storage types.
    """

    def setUp(self):
        user = User.objects.create_user('admin', 'admin@example.com',
                                        'password')
        user.is_staff = True
        user.is_superuser = True
        user.save()
        self.client.login(username='admin', password='password')

    def assert_string_in_response(self, filename, input_format, encoding=None):
        input_format = input_format
        filename = os.path.join(
            os.path.dirname(__file__),
            os.path.pardir,
            'exports',
            filename)
        with open(filename, "rb") as f:
            data = {
                'input_format': input_format,
                'import_file': f,
            }
            if encoding:
                BookAdmin.from_encoding = encoding
            response = self.client.post('/admin/core/book/import/', data)
        self.assertEqual(response.status_code, 200)
        self.assertIn('result', response.context)
        self.assertFalse(response.context['result'].has_errors())
        self.assertContains(response, 'test@example.com')

    @override_settings(IMPORT_EXPORT_TMP_STORAGE_CLASS='import_export.tmp_storages.TempFolderStorage')
    def test_import_action_handles_TempFolderStorage_read(self):
        self.assert_string_in_response('books.csv', '0')

    @override_settings(IMPORT_EXPORT_TMP_STORAGE_CLASS='import_export.tmp_storages.TempFolderStorage')
    def test_import_action_handles_TempFolderStorage_read_mac(self):
        self.assert_string_in_response('books-mac.csv', '0')

    @override_settings(IMPORT_EXPORT_TMP_STORAGE_CLASS='import_export.tmp_storages.TempFolderStorage')
    def test_import_action_handles_TempFolderStorage_read_iso_8859_1(self):
        self.assert_string_in_response('books-ISO-8859-1.csv', '0', 'ISO-8859-1')

    @override_settings(IMPORT_EXPORT_TMP_STORAGE_CLASS='import_export.tmp_storages.TempFolderStorage')
    def test_import_action_handles_TempFolderStorage_read_binary(self):
        self.assert_string_in_response('books.xls', '1')

    @override_settings(IMPORT_EXPORT_TMP_STORAGE_CLASS='import_export.tmp_storages.CacheStorage')
    def test_import_action_handles_CacheStorage_read(self):
        self.assert_string_in_response('books.csv', '0')

    @override_settings(IMPORT_EXPORT_TMP_STORAGE_CLASS='import_export.tmp_storages.CacheStorage')
    def test_import_action_handles_CacheStorage_read_mac(self):
        self.assert_string_in_response('books-mac.csv', '0')

    @override_settings(IMPORT_EXPORT_TMP_STORAGE_CLASS='import_export.tmp_storages.CacheStorage')
    def test_import_action_handles_CacheStorage_read_iso_8859_1(self):
        self.assert_string_in_response('books-ISO-8859-1.csv', '0', 'ISO-8859-1')

    @override_settings(IMPORT_EXPORT_TMP_STORAGE_CLASS='import_export.tmp_storages.CacheStorage')
    def test_import_action_handles_CacheStorage_read_binary(self):
        self.assert_string_in_response('books.xls', '1')

    @override_settings(IMPORT_EXPORT_TMP_STORAGE_CLASS='import_export.tmp_storages.MediaStorage')
    def test_import_action_handles_MediaStorage_read(self):
        self.assert_string_in_response('books.csv', '0')

    @override_settings(IMPORT_EXPORT_TMP_STORAGE_CLASS='import_export.tmp_storages.MediaStorage')
    def test_import_action_handles_MediaStorage_read_mac(self):
        self.assert_string_in_response('books-mac.csv', '0')

    @override_settings(IMPORT_EXPORT_TMP_STORAGE_CLASS='import_export.tmp_storages.MediaStorage')
    def test_import_action_handles_MediaStorage_read_iso_8859_1(self):
        self.assert_string_in_response('books-ISO-8859-1.csv', '0', 'ISO-8859-1')

    @override_settings(IMPORT_EXPORT_TMP_STORAGE_CLASS='import_export.tmp_storages.MediaStorage')
    def test_import_action_handles_MediaStorage_read_binary(self):
        self.assert_string_in_response('books.xls', '1')


class CompleteImportEncodingTest(TestCase):
    """Test handling 'complete import' step using different file encodings
    and storage types.
    """

    def setUp(self):
        user = User.objects.create_user('admin', 'admin@example.com',
                                        'password')
        user.is_staff = True
        user.is_superuser = True
        user.save()
        self.client.login(username='admin', password='password')

    def assert_string_in_response(self, filename, input_format, encoding=None):
        input_format = input_format
        filename = os.path.join(
            os.path.dirname(__file__),
            os.path.pardir,
            'exports',
            filename)
        with open(filename, "rb") as f:
            data = {
                'input_format': input_format,
                'import_file': f,
            }
            if encoding:
                BookAdmin.from_encoding = encoding
            response = self.client.post('/admin/core/book/import/', data)

        confirm_form = response.context['confirm_form']
        data = confirm_form.initial
        response = self.client.post('/admin/core/book/process_import/', data, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Import finished, with 1 new and 0 updated books.')

    @override_settings(IMPORT_EXPORT_TMP_STORAGE_CLASS='import_export.tmp_storages.TempFolderStorage')
    def test_import_action_handles_TempFolderStorage_read(self):
        self.assert_string_in_response('books.csv', '0')

    @override_settings(IMPORT_EXPORT_TMP_STORAGE_CLASS='import_export.tmp_storages.TempFolderStorage')
    def test_import_action_handles_TempFolderStorage_read_mac(self):
        self.assert_string_in_response('books-mac.csv', '0')

    @override_settings(IMPORT_EXPORT_TMP_STORAGE_CLASS='import_export.tmp_storages.TempFolderStorage')
    def test_import_action_handles_TempFolderStorage_read_iso_8859_1(self):
        self.assert_string_in_response('books-ISO-8859-1.csv', '0', 'ISO-8859-1')

    @override_settings(IMPORT_EXPORT_TMP_STORAGE_CLASS='import_export.tmp_storages.TempFolderStorage')
    def test_import_action_handles_TempFolderStorage_read_binary(self):
        self.assert_string_in_response('books.xls', '1')

    @override_settings(IMPORT_EXPORT_TMP_STORAGE_CLASS='import_export.tmp_storages.CacheStorage')
    def test_import_action_handles_CacheStorage_read(self):
        self.assert_string_in_response('books.csv', '0')

    @override_settings(IMPORT_EXPORT_TMP_STORAGE_CLASS='import_export.tmp_storages.CacheStorage')
    def test_import_action_handles_CacheStorage_read_mac(self):
        self.assert_string_in_response('books-mac.csv', '0')

    @override_settings(IMPORT_EXPORT_TMP_STORAGE_CLASS='import_export.tmp_storages.CacheStorage')
    def test_import_action_handles_CacheStorage_read_iso_8859_1(self):
        self.assert_string_in_response('books-ISO-8859-1.csv', '0', 'ISO-8859-1')

    @override_settings(IMPORT_EXPORT_TMP_STORAGE_CLASS='import_export.tmp_storages.CacheStorage')
    def test_import_action_handles_CacheStorage_read_binary(self):
        self.assert_string_in_response('books.xls', '1')

    @override_settings(IMPORT_EXPORT_TMP_STORAGE_CLASS='import_export.tmp_storages.MediaStorage')
    def test_import_action_handles_MediaStorage_read(self):
        self.assert_string_in_response('books.csv', '0')

    @override_settings(IMPORT_EXPORT_TMP_STORAGE_CLASS='import_export.tmp_storages.MediaStorage')
    def test_import_action_handles_MediaStorage_read_mac(self):
        self.assert_string_in_response('books-mac.csv', '0')

    @override_settings(IMPORT_EXPORT_TMP_STORAGE_CLASS='import_export.tmp_storages.MediaStorage')
    def test_import_action_handles_MediaStorage_read_iso_8859_1(self):
        self.assert_string_in_response('books-ISO-8859-1.csv', '0', 'ISO-8859-1')

    @override_settings(IMPORT_EXPORT_TMP_STORAGE_CLASS='import_export.tmp_storages.MediaStorage')
    def test_import_action_handles_MediaStorage_read_binary(self):
        self.assert_string_in_response('books.xls', '1')


class TestImportExportActionModelAdmin(ImportExportActionModelAdmin):
    def __init__(self, mock_model, mock_site, error_instance):
        self.error_instance = error_instance
        super().__init__(mock_model, mock_site)

    def write_to_tmp_storage(self, import_file, input_format):
        mock_storage = MagicMock(spec=TempFolderStorage)

        mock_storage.read.side_effect = self.error_instance
        return mock_storage


class ExportActionAdminIntegrationTest(TestCase):

    def setUp(self):
        user = User.objects.create_user('admin', 'admin@example.com',
                                        'password')
        user.is_staff = True
        user.is_superuser = True
        user.save()

        self.cat1 = Category.objects.create(name='Cat 1')
        self.cat2 = Category.objects.create(name='Cat 2')

        self.client.login(username='admin', password='password')

    def test_export(self):
        data = {
            'action': ['export_admin_action'],
            'file_format': '0',
            '_selected_action': [str(self.cat1.id)],
        }
        response = self.client.post('/admin/core/category/', data)
        self.assertContains(response, self.cat1.name, status_code=200)
        self.assertNotContains(response, self.cat2.name, status_code=200)
        self.assertTrue(response.has_header("Content-Disposition"))
        date_str = datetime.now().strftime('%Y-%m-%d')
        self.assertEqual(
            response['Content-Disposition'],
            'attachment; filename="Category-{}.csv"'.format(date_str)
        )

    def test_export_no_format_selected(self):
        data = {
            'action': ['export_admin_action'],
            '_selected_action': [str(self.cat1.id)],
        }
        response = self.client.post('/admin/core/category/', data)
        self.assertEqual(response.status_code, 302)

    def test_get_export_data_raises_PermissionDenied_when_no_export_permission_assigned(self):
        request = MagicMock(spec=HttpRequest)

        class TestMixin(ExportMixin):
            model = Book

            def has_export_permission(self, request):
                return False
        m = TestMixin()
        with self.assertRaises(PermissionDenied):
            m.get_export_data('0', Book.objects.none(), request=request)

    def test_export_admin_action_one_formats(self):
        mock_model = mock.MagicMock()
        mock_site = mock.MagicMock()

        class TestCategoryAdmin(ExportActionModelAdmin):
            def __init__(self):
                super().__init__(mock_model, mock_site)

            formats = [base_formats.CSV]

        m = TestCategoryAdmin()
        action_form = m.action_form
 
        items = list(action_form.base_fields.items())
        file_format = items[len(items)-1][1]
        choices = file_format.choices

        self.assertNotEqual(choices[0][0], '---')
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

            formats = [base_formats.CSV, base_formats.JSON]

        m = TestCategoryAdmin()
        action_form = m.action_form
 
        items = list(action_form.base_fields.items())
        file_format = items[len(items)-1][1]
        choices = file_format.choices

        self.assertEqual(choices[0][1], "---")
        self.assertEqual(len(choices), 9)

        m = TestFormatsCategoryAdmin()
        action_form = m.action_form
 
        items = list(action_form.base_fields.items())
        file_format = items[len(items)-1][1]
        choices = file_format.choices

        self.assertEqual(choices[0][1], "---")
        self.assertEqual(len(m.formats) + 1, len(choices))

        self.assertIn('csv', [c[1] for c in choices])
        self.assertIn('json', [c[1] for c in choices])


class TestExportEncoding(TestCase):
    mock_request = MagicMock(spec=HttpRequest)
    mock_request.POST = {'file_format': 0}

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
        data = self.export_mixin.get_export_data(self.file_format, list(), request=self.mock_request)
        csv_dataset = tablib.import_set(data)
        self.assertEqual("teststr", csv_dataset.dict[0]["name"])

    def test_to_encoding_set(self):
        self.export_mixin = self.TestMixin(test_str="ハローワールド")
        data = self.export_mixin.get_export_data(self.file_format, list(), request=self.mock_request, encoding="shift-jis")
        encoding = chardet.detect(bytes(data))["encoding"]
        self.assertEqual("SHIFT_JIS", encoding)

    def test_to_encoding_set_incorrect(self):
        self.export_mixin = self.TestMixin()
        with self.assertRaises(LookupError):
            self.export_mixin.get_export_data(self.file_format, list(), request=self.mock_request, encoding="bad-encoding")

    def test_to_encoding_not_set_for_binary_file(self):
        self.export_mixin = self.TestMixin(test_str="teststr")
        self.file_format = formats.base_formats.XLSX()
        data = self.export_mixin.get_export_data(self.file_format, list(), request=self.mock_request)
        binary_dataset = tablib.import_set(data)
        self.assertEqual("teststr", binary_dataset.dict[0]["name"])

    @mock.patch("import_export.admin.ImportForm")
    def test_export_action_to_encoding(self, mock_form):
        mock_form.is_valid.return_value = True
        self.export_mixin.to_encoding = "utf-8"
        with mock.patch("import_export.admin.ExportMixin.get_export_data") as mock_get_export_data:
            self.export_mixin.export_action(self.mock_request)
            encoding_kwarg = mock_get_export_data.call_args_list[0][1]["encoding"]
            self.assertEqual("utf-8", encoding_kwarg)

    @mock.patch("import_export.admin.ImportForm")
    def test_export_admin_action_to_encoding(self, mock_form):
        class TestExportActionMixin(ExportActionMixin):
            def get_export_filename(self, request, queryset, file_format):
                return "f"

        self.mock_request.POST = {'file_format': '1'}

        self.export_mixin = TestExportActionMixin()
        self.export_mixin.to_encoding = "utf-8"
        mock_form.is_valid.return_value = True
        with mock.patch("import_export.admin.ExportMixin.get_export_data") as mock_get_export_data:
            self.export_mixin.export_admin_action(self.mock_request, list())
            encoding_kwarg = mock_get_export_data.call_args_list[0][1]["encoding"]
            self.assertEqual("utf-8", encoding_kwarg)
