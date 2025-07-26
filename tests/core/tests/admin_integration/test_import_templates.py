import os
from unittest.mock import patch
from urllib.parse import urlencode

from core.admin import CustomBookAdmin, ImportMixin
from core.models import Author, EBook
from core.tests.admin_integration.mixins import AdminTestMixin
from django.test.testcases import TestCase
from django.test.utils import override_settings
from django.utils.translation import gettext_lazy as _


class ImportTemplateTests(AdminTestMixin, TestCase):

    def test_import_export_template(self):
        response = self._get_url_response(self.core_book_url)
        self.assertTemplateUsed(response, self.change_list_template_url)
        self.assertTemplateUsed(response, self.change_list_url)
        self.assertTemplateUsed(response, self.change_list_url)
        self.assertContains(response, _("Import"))
        self.assertContains(response, _("Export"))
        self.assertContains(response, "Custom change list item")

    @patch("import_export.admin.logger")
    def test_issue_1521_change_list_template_as_property(self, mock_logger):
        # Test that a warning is logged when change_list_template is a property
        class TestImportCls(ImportMixin):
            @property
            def change_list_template(self):
                return ["x"]

        TestImportCls()
        mock_logger.warning.assert_called_once_with(
            "failed to assign change_list_template attribute"
        )

    @override_settings(DEBUG=True)
    def test_correct_scripts_declared_when_debug_is_true(self):
        # GET the import form
        response = self._get_url_response(
            self.book_import_url, str_in_response="form action="
        )
        self.assertTemplateUsed(response, self.admin_import_template_url)
        self.assertContains(
            response,
            '<script src="/static/admin/js/vendor/jquery/jquery.js">',
            count=1,
            html=True,
        )
        self.assertContains(
            response,
            '<script src="/static/admin/js/jquery.init.js">',
            count=1,
            html=True,
        )
        self.assertContains(
            response,
            '<script src="/static/import_export/guess_format.js">',
            count=1,
            html=True,
        )

    @override_settings(DEBUG=False)
    def test_correct_scripts_declared_when_debug_is_false(self):
        # GET the import form
        response = self._get_url_response(self.book_import_url)
        self.assertTemplateUsed(response, self.admin_import_template_url)
        self.assertContains(response, 'form action=""')
        self.assertContains(
            response,
            '<script src="/static/admin/js/vendor/jquery/jquery.min.js">',
            count=1,
            html=True,
        )
        self.assertContains(
            response,
            '<script src="/static/admin/js/jquery.init.js">',
            count=1,
            html=True,
        )
        self.assertContains(
            response,
            '<script src="/static/import_export/guess_format.js">',
            count=1,
            html=True,
        )

    def test_import_with_customized_forms(self):
        """Test if admin import works if forms are customized"""
        # We reuse import scheme from `test_import` to import books.csv.
        # We use customized BookAdmin (CustomBookAdmin) with modified import
        # form, which requires Author to be selected (from available authors).
        # Note that url is /admin/core/ebook/import (and not: ...book/import)!

        # We need at least a single author in the db to select from in the
        # admin import custom forms
        Author.objects.create(id=11, name="Test Author")

        # GET the import form
        response = self._get_url_response(self.ebook_import_url)
        self.assertTemplateUsed(response, self.import_export_import_template_url)
        self.assertContains(response, 'form action=""')

        # POST the import form
        input_format = "0"
        filename = os.path.join(
            os.path.dirname(__file__),
            os.path.pardir,
            os.path.pardir,
            "exports",
            "books.csv",
        )
        with open(filename, "rb") as fobj:
            data = {"author": 11, "format": input_format, "import_file": fobj}
            response = self._post_url_response(self.ebook_import_url, data)
        self.assertIn("result", response.context)
        self.assertFalse(response.context["result"].has_errors())
        self.assertIn("confirm_form", response.context)
        confirm_form = response.context["confirm_form"]
        self.assertIsInstance(
            confirm_form,
            CustomBookAdmin(EBook, "ebook/import").get_confirm_form_class(None),
        )

        data = confirm_form.initial
        self.assertEqual(data["original_file_name"], "books.csv")
        response = self._post_url_response(
            self.process_ebook_import_url, data, follow=True
        )
        self.assertContains(
            response,
            _(
                "Import finished: {} new, {} updated, {} deleted and {} skipped {}."
            ).format(1, 0, 0, 0, EBook._meta.verbose_name_plural),
        )

    def test_import_form_action_conditional_query_string(self):
        """
        Test that the form action is clean
        (no trailing '?') when no GET params
        are present.
        """

        # 1. Test no GET parameters → form action has no trailing '?'
        response_no_get = self._get_url_response(self.book_import_url)
        html_no_get = response_no_get.content.decode()

        expected_action_no_get = (
            '<form action="" method="post" enctype="multipart/form-data">'
        )
        self.assertIn(expected_action_no_get, html_no_get)
        self.assertIn(expected_action_no_get, html_no_get)
        self.assertNotIn(f"{self.book_import_url}?", html_no_get)

    def test_import_confirm_form_action_conditional_querystring(self):
        """
        The confirm import form should include a query string
        in its action ONLY when GET params are present, i.e. action="?foo=bar" etc.
        """
        Author.objects.create(id=1, name="Test Author")

        # Prepare GET params
        params = {"test": "1"}
        paramstr = urlencode(params)
        import_url = f"{self.ebook_import_url}?{paramstr}"

        # Simulate POST to the import form to trigger the confirmation step
        input_format = "0"
        filename = os.path.join(
            os.path.dirname(__file__),
            os.path.pardir,
            os.path.pardir,
            "exports",
            "books.csv",
        )
        with open(filename, "rb") as fobj:
            data = {"author": 1, "format": input_format, "import_file": fobj}
            # POST to the import form with GET parameters
            response = self._post_url_response(import_url, data)

        # confirm_form should be in context—so confirm import block is used
        html = response.content.decode()

        # check that confirm_form is present
        self.assertIn('name="confirm"', html)
        self.assertIn("Confirm import", html)

        expected = (
            f'<form action="{self.process_ebook_import_url}?test=1" method="POST">'
        )
        self.assertIn(expected, html)
