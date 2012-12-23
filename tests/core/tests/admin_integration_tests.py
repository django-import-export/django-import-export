import os.path

from django.test.testcases import TestCase
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _


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

    def test_import(self):
        input_format = '0'
        filename = os.path.join(
                os.path.dirname(__file__),
                os.path.pardir,
                'exports',
                'books.csv')
        data = {
                'input_format': input_format,
                'import_file': open(filename),
                }
        response = self.client.post('/admin/core/book/import/', data)
        self.assertEqual(response.status_code, 200)
        self.assertIn('result', response.context)
        self.assertFalse(response.context['result'].has_errors())
        self.assertIn('confirm_form', response.context)
        confirm_form = response.context['confirm_form']

        data = confirm_form.initial
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
