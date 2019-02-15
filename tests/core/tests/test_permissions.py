import os.path

from django.contrib.auth.models import Permission, User
from django.test.testcases import TestCase
from django.test.utils import override_settings


class ImportExportPermissionTest(TestCase):

    def setUp(self):
        user = User.objects.create_user('admin', 'admin@example.com',
                                        'password')
        user.is_staff = True
        user.is_superuser = False
        user.save()

        self.user = user
        self.client.login(username='admin', password='password')

    def set_user_book_model_permission(self, action):
        permission = Permission.objects.get(codename="%s_book" % action)
        self.user.user_permissions.add(permission)

    @override_settings(IMPORT_EXPORT_IMPORT_PERMISSION_CODE='change')
    def test_import(self):
        # user has no permission to import
        response = self.client.get('/admin/core/book/import/')
        self.assertEqual(response.status_code, 403)

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
            self.assertEqual(response.status_code, 403)

            response = self.client.post('/admin/core/book/process_import/', {})
            self.assertEqual(response.status_code, 403)

        # user has sufficient permission to import
        self.set_user_book_model_permission('change')

        response = self.client.get('/admin/core/book/import/')
        self.assertEqual(response.status_code, 200)

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
            confirm_form = response.context['confirm_form']

            data = confirm_form.initial
            response = self.client.post('/admin/core/book/process_import/', data)
            self.assertEqual(response.status_code, 302)


    @override_settings(IMPORT_EXPORT_EXPORT_PERMISSION_CODE='change')
    def test_import_with_permission_set(self):
        response = self.client.get('/admin/core/book/export/')
        self.assertEqual(response.status_code, 403)

        data = {'file_format': '0'}
        response = self.client.post('/admin/core/book/export/', data)
        self.assertEqual(response.status_code, 403)

        self.set_user_book_model_permission('change')
        response = self.client.get('/admin/core/book/export/')
        self.assertEqual(response.status_code, 200)

        data = {'file_format': '0'}
        response = self.client.post('/admin/core/book/export/', data)
        self.assertEqual(response.status_code, 200)

    @override_settings(IMPORT_EXPORT_EXPORT_PERMISSION_CODE='add')
    def test_check_export_button(self):
        self.set_user_book_model_permission('change')

        response = self.client.get('/admin/core/book/')
        widget = "import_link"
        self.assertIn(widget, response.content.decode())
        widget = "export_link"
        self.assertNotIn(widget, response.content.decode())

    @override_settings(IMPORT_EXPORT_IMPORT_PERMISSION_CODE='add')
    def test_check_import_button(self):
        self.set_user_book_model_permission('change')

        response = self.client.get('/admin/core/book/')
        widget = "import_link"
        self.assertNotIn(widget, response.content.decode())
        widget = "export_link"
        self.assertIn(widget, response.content.decode())
