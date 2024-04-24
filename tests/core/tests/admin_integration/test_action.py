from datetime import datetime
from unittest import mock
from unittest.mock import MagicMock

from core.admin import CategoryAdmin
from core.models import Book, Category
from core.tests.admin_integration.mixins import AdminTestMixin
from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest
from django.test import RequestFactory
from django.test.testcases import TestCase
from django.test.utils import override_settings
from django.urls import reverse

from import_export.admin import ExportMixin


class ExportActionAdminIntegrationTest(AdminTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.cat1 = Category.objects.create(name="Cat 1")
        self.cat2 = Category.objects.create(name="Cat 2")
        # fields payload for `CategoryResource` -
        # to export using `SelectableFieldsExportForm`
        self.resource_fields_payload = {
            "categoryresource_id": True,
            "categoryresource_name": True,
        }

    def _check_export_response(self, response):
        self.assertContains(response, self.cat1.name, status_code=200)
        self.assertNotContains(response, self.cat2.name, status_code=200)
        self.assertTrue(response.has_header("Content-Disposition"))
        date_str = datetime.now().strftime("%Y-%m-%d")
        self.assertEqual(
            response["Content-Disposition"],
            'attachment; filename="Category-{}.csv"'.format(date_str),
        )

    @override_settings(IMPORT_EXPORT_SKIP_ADMIN_ACTION_EXPORT_UI=True)
    def test_export_skips_export_ui_page(self):
        data = {
            "action": ["export_admin_action"],
            "_selected_action": [str(self.cat1.id)],
        }
        response = self.client.post("/admin/core/category/", data)
        self._check_export_response(response)

    def test_export_displays_ui_select_page(self):
        data = {
            "action": ["export_admin_action"],
            "_selected_action": [str(self.cat1.id)],
        }
        response = self.client.post("/admin/core/category/", data)

        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)
        export_form = response.context["form"]
        data = export_form.initial
        self.assertEqual([self.cat1.id], data["export_items"])
        self.assertIn("Export 1 selected item.", str(response.content))

    def test_export_displays_ui_select_page_multiple_items(self):
        data = {
            "action": ["export_admin_action"],
            "_selected_action": [str(self.cat1.id), str(self.cat2.id)],
        }
        response = self.client.post("/admin/core/category/", data)

        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)
        export_form = response.context["form"]
        data = export_form.initial
        self.assertEqual(
            sorted([self.cat1.id, self.cat2.id]), sorted(data["export_items"])
        )
        self.assertIn("Export 2 selected items.", str(response.content))

    def test_export_post(self):
        # create a POST request with data selected from the 'action' export
        data = {
            "format": "0",
            "export_items": [str(self.cat1.id)],
            **self.resource_fields_payload,
        }
        date_str = datetime.now().strftime("%Y-%m-%d")
        response = self.client.post("/admin/core/category/export/", data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.has_header("Content-Disposition"))
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertEqual(
            response["Content-Disposition"],
            'attachment; filename="Category-{}.csv"'.format(date_str),
        )
        target_str = f"id,name\r\n{self.cat1.id},Cat 1\r\n"
        self.assertEqual(target_str.encode(), response.content)

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
            self.assertTrue(200 <= response.status_code <= 399)
            mock_export_admin_action.assert_called()

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
            m.get_export_data("0", request, Book.objects.none())


class TestExportButtonOnChangeForm(AdminTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.cat1 = Category.objects.create(name="Cat 1")
        self.change_url = reverse(
            "%s:%s_%s_change"
            % (
                "admin",
                "core",
                "category",
            ),
            args=[self.cat1.id],
        )
        self.target_str = (
            '<input type="submit" value="Export" '
            'class="default" name="_export-item">'
        )

    def test_export_button_on_change_form(self):
        response = self.client.get(self.change_url)
        self.assertIn(
            self.target_str,
            str(response.content),
        )
        response = self.client.post(
            self.change_url, data={"_export-item": "Export", "name": self.cat1.name}
        )
        self.assertIn("Export 1 selected item", str(response.content))

    def test_save_button_on_change_form(self):
        # test default behavior is retained when saving an instance ChangeForm
        response = self.client.post(
            self.change_url, data={"_save": "Save", "name": self.cat1.name}, follow=True
        )
        target_str = f"The category.*{self.cat1.name}.*was changed successfully."
        self.assertRegex(str(response.content), target_str)

    def test_export_button_on_change_form_disabled(self):
        class MockCategoryAdmin(CategoryAdmin):
            show_change_form_export = True

        factory = RequestFactory()
        category_admin = MockCategoryAdmin(Category, admin.site)

        request = factory.get(self.change_url)
        request.user = self.user

        response = category_admin.change_view(request, str(self.cat1.id))
        response.render()

        self.assertIn(self.target_str, str(response.content))

        category_admin.show_change_form_export = False
        response = category_admin.change_view(request, str(self.cat1.id))
        response.render()
        self.assertNotIn(self.target_str, str(response.content))
