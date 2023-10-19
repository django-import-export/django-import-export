from datetime import datetime
from unittest import mock
from unittest.mock import MagicMock, patch

from core.models import Book, Category
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest
from django.test.testcases import TestCase
from django.test.utils import override_settings

from import_export.admin import ExportActionModelAdmin, ExportMixin
from import_export.formats import base_formats
from tests.core.tests.admin_integration import AdminTestMixin
from tests.core.tests.admin_integration.test_admin_integration_utils import (
    AdminTestMixin,
)


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
