from datetime import datetime
from unittest.mock import MagicMock

from core.models import Book, Category
from core.tests.admin_integration.mixins import AdminTestMixin
from core.tests.utils import ignore_widget_deprecation_warning
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest
from django.test.testcases import TestCase
from django.test.utils import override_settings

from import_export.admin import ExportMixin, ImportExportActionModelAdmin
from import_export.tmp_storages import TempFolderStorage


class ExportActionAdminIntegrationTest(AdminTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.cat1 = Category.objects.create(name="Cat 1")
        self.cat2 = Category.objects.create(name="Cat 2")

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
    @ignore_widget_deprecation_warning
    def test_export_skips_export_ui_page(self):
        data = {
            "action": ["export_admin_action"],
            "_selected_action": [str(self.cat1.id)],
        }
        response = self.client.post("/admin/core/category/", data)
        self._check_export_response(response)

    @ignore_widget_deprecation_warning
    def test_export_redirects_to_export_ui_select_page(self):
        data = {
            "action": ["export_admin_action"],
            "_selected_action": [str(self.cat1.id)],
        }
        response = self.client.post("/admin/core/category/", data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual("/admin/core/category/export/?ia=1", response.url)
        self.assertEqual([self.cat1.pk], self.client.session["export_items"])

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


class TestImportExportActionModelAdmin(ImportExportActionModelAdmin):
    def __init__(self, mock_model, mock_site, error_instance):
        self.error_instance = error_instance
        super().__init__(mock_model, mock_site)

    def write_to_tmp_storage(self, import_file, input_format):
        mock_storage = MagicMock(spec=TempFolderStorage)

        mock_storage.read.side_effect = self.error_instance
        return mock_storage