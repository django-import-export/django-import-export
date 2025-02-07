import os.path

from core.models import Category
from core.tests.admin_integration.mixins import AdminTestMixin
from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType
from django.test.testcases import TestCase
from django.test.utils import override_settings
from django.urls import reverse


class ImportExportPermissionTest(AdminTestMixin, TestCase):
    def setUp(self):
        user = User.objects.create_user("admin", "admin@example.com", "password")
        user.is_staff = True
        user.is_superuser = False
        user.save()

        self.user = user
        self.client.login(username="admin", password="password")

    def set_user_model_permission(self, action, model_name):
        permission = Permission.objects.get(codename=f"{action}_{model_name}")
        self.user.user_permissions.add(permission)

    @override_settings(IMPORT_EXPORT_IMPORT_PERMISSION_CODE="change")
    def test_import(self):
        # user has no permission to import
        response = self.client.get(self.book_import_url)
        self.assertEqual(response.status_code, 403)

        # POST the import form
        input_format = "0"
        filename = os.path.join(
            os.path.dirname(__file__), os.path.pardir, "exports", "books.csv"
        )

        with open(filename, "rb") as f:
            data = {
                "format": input_format,
                "import_file": f,
            }

            response = self.client.post(self.book_import_url, data)
            self.assertEqual(response.status_code, 403)

            response = self.client.post(self.book_process_import_url, {})
            self.assertEqual(response.status_code, 403)

        # user has sufficient permission to import
        self.set_user_model_permission("change", "book")

        response = self.client.get(self.book_import_url)
        self.assertEqual(response.status_code, 200)

        # POST the import form
        input_format = "0"
        filename = os.path.join(
            os.path.dirname(__file__), os.path.pardir, "exports", "books.csv"
        )

        with open(filename, "rb") as f:
            data = {
                "format": input_format,
                "import_file": f,
            }

            response = self.client.post(self.book_import_url, data)
            self.assertEqual(response.status_code, 200)
            confirm_form = response.context["confirm_form"]

            data = confirm_form.initial
            response = self.client.post(self.book_process_import_url, data)
            self.assertEqual(response.status_code, 302)

    @override_settings(IMPORT_EXPORT_EXPORT_PERMISSION_CODE="change")
    def test_export_with_permission_set(self):
        response = self.client.get(self.book_export_url)
        self.assertEqual(response.status_code, 403)

        data = {"format": "0"}
        response = self.client.post(self.book_export_url, data)
        self.assertEqual(response.status_code, 403)

        self.set_user_model_permission("change", "book")
        response = self.client.get(self.book_export_url)
        self.assertEqual(response.status_code, 200)

        data = {"format": "0"}
        response = self.client.post(self.book_export_url, data)
        self.assertEqual(response.status_code, 200)

    @override_settings(IMPORT_EXPORT_EXPORT_PERMISSION_CODE="change")
    def test_export_action_with_permission_set(self):
        self.cat1 = Category.objects.create(name="Cat 1")
        data = {
            "action": ["export_admin_action"],
            "_selected_action": [str(self.cat1.id)],
        }
        response = self.client.post(self.category_change_url, data)
        self.assertEqual(response.status_code, 403)

        self.set_user_model_permission("change", "category")
        response = self.client.post(self.category_change_url, data)
        self.assertEqual(response.status_code, 200)

    @override_settings(IMPORT_EXPORT_EXPORT_PERMISSION_CODE="add")
    def test_check_export_button(self):
        self.set_user_model_permission("change", "book")

        response = self.client.get(self.core_book_url)
        widget = "import_link"
        self.assertIn(widget, response.content.decode())
        widget = "export_link"
        self.assertNotIn(widget, response.content.decode())

    @override_settings(IMPORT_EXPORT_IMPORT_PERMISSION_CODE="add")
    def test_check_import_button(self):
        self.set_user_model_permission("change", "book")

        response = self.client.get(self.core_book_url)
        widget = "import_link"
        self.assertNotIn(widget, response.content.decode())
        widget = "export_link"
        self.assertIn(widget, response.content.decode())

    @override_settings(IMPORT_EXPORT_EXPORT_PERMISSION_CODE="export")
    def test_export_button_for_export_permission(self):
        content_type = ContentType.objects.get_for_model(Category)
        Permission.objects.create(
            codename="export_category",
            name="Can export category",
            content_type=content_type,
        )
        self.set_user_model_permission("view", "category")
        self.cat1 = Category.objects.create(name="Cat 1")
        self.change_url = reverse(
            "%s:%s_%s_change"
            % (
                "admin",
                "core",
                "category",
            ),
            args=[self.cat1.pk],
        )
        response = self.client.get(self.change_url)
        export_btn = (
            '<input type="submit" value="Export" class="default" name="_export-item">'
        )
        self.assertNotIn(export_btn, response.content.decode())

        # add export permission and the button should be displayed
        self.set_user_model_permission("export", "category")
        response = self.client.get(self.change_url)
        self.assertIn(export_btn, response.content.decode())

    @override_settings(IMPORT_EXPORT_EXPORT_PERMISSION_CODE="export")
    def test_action_dropdown_contains_export_action(self):
        content_type = ContentType.objects.get_for_model(Category)
        Permission.objects.create(
            codename="export_category",
            name="Can export category",
            content_type=content_type,
        )
        self.set_user_model_permission("view", "category")
        self.cat1 = Category.objects.create(name="Cat 1")

        response = self.client.get(self.category_change_url)
        export_option = (
            '<option value="export_admin_action">Export selected categories</option>'
        )
        self.assertNotIn(export_option, response.content.decode())

        # add export permission and the button should be displayed
        self.set_user_model_permission("export", "category")
        response = self.client.get(self.category_change_url)
        self.assertIn(export_option, response.content.decode())
