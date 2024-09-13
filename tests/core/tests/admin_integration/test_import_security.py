import os

from core.admin import AuthorAdmin, BookAdmin
from core.tests.admin_integration.mixins import AdminTestMixin
from django.test.testcases import TestCase
from django.utils.translation import gettext_lazy as _


class ImportAdminSecurityTests(AdminTestMixin, TestCase):

    def test_csrf(self):
        self._get_url_response(self.book_process_import_url, expected_status_code=405)

    def test_import_file_name_in_tempdir(self):
        # 65 - import_file_name form field can be use to access the filesystem
        import_file_name = os.path.join(
            os.path.dirname(__file__), os.path.pardir, "exports", "books.csv"
        )
        data = {
            "format": "0",
            "import_file_name": import_file_name,
            "original_file_name": "books.csv",
        }
        with self.assertRaises(FileNotFoundError):
            self._post_url_response(self.book_process_import_url, data)

    def test_import_buttons_visible_without_add_permission(self):
        # When using ImportMixin, users should be able to see the import button
        # without add permission (to be consistent with ImportExportMixin)

        original = AuthorAdmin.has_add_permission
        AuthorAdmin.has_add_permission = lambda self, request: False
        response = self._get_url_response(self.core_author_url)
        AuthorAdmin.has_add_permission = original

        self.assertContains(response, _("Import"))
        self.assertTemplateUsed(response, self.change_list_url)

    def test_import_export_buttons_visible_without_add_permission(self):
        # issue 38 - Export button not visible when no add permission
        original = BookAdmin.has_add_permission
        BookAdmin.has_add_permission = lambda self, request: False
        response = self._get_url_response(self.book_import_url)
        BookAdmin.has_add_permission = original

        self.assertContains(response, _("Export"))
        self.assertContains(response, _("Import"))
