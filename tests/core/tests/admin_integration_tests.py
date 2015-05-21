from __future__ import unicode_literals

import os.path

from django.test.utils import override_settings
from django.test.testcases import TestCase
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from django.contrib.admin.models import LogEntry

from core.admin import BookAdmin
from core.models import Category


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
        self.assertContains(response, _('Import finished'))

    def test_export(self):
        response = self.client.get('/admin/core/book/export/')
        self.assertEqual(response.status_code, 200)

        data = {
                'file_format': '0',
                }
        response = self.client.post('/admin/core/book/export/', data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.has_header("Content-Disposition"))
        self.assertEqual(response['Content-Type'], 'text/csv')

    def test_import_export_buttons_visible_without_add_permission(self):
        # issue 38 - Export button not visible when no add permission
        original = BookAdmin.has_add_permission
        BookAdmin.has_add_permission = lambda self, request: False
        response = self.client.get('/admin/core/book/')
        BookAdmin.has_add_permission = original

        self.assertContains(response, _('Export'))
        self.assertContains(response, _('Import'))

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
        with self.assertRaises(IOError):
            self.client.post('/admin/core/book/process_import/', data)

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

    def test_export_no_format_selected(self):
        data = {
            'action': ['export_admin_action'],
            '_selected_action': [str(self.cat1.id)],
        }
        response = self.client.post('/admin/core/category/', data)
        self.assertEqual(response.status_code, 302)
