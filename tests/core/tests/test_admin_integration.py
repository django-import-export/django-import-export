import os.path
from datetime import datetime
from tablib import Dataset

from core.admin import AuthorAdmin, BookAdmin, BookResource, CustomBookAdmin
from core.models import Author, Book, Category, EBook, Parent

from django.contrib.admin.models import LogEntry
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test.testcases import TestCase
from django.test.utils import override_settings
from django.utils.translation import gettext_lazy as _

from import_export.formats.base_formats import DEFAULT_FORMATS


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
        def get_resource_class(self):
            return R

        # Verify that when an exception occurs in import_row, when raise_errors is False,
        # the returned row result has a correct import_type value,
        # so generating log entries does not fail.
        @monkeypatch_method(BookAdmin)
        def process_dataset(self, dataset, confirm_form, request, *args, **kwargs):
            resource = self.get_import_resource_class()(**self.get_import_resource_kwargs(request, *args, **kwargs))
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
