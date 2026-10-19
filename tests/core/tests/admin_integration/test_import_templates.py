import os

from core.admin import CustomBookAdmin
from core.models import Author, Book, EBook
from core.tests.admin_integration.mixins import AdminTestMixin
from django.contrib import admin
from django.contrib.admin.options import ModelAdmin
from django.template import TemplateDoesNotExist
from django.template.response import TemplateResponse
from django.test import RequestFactory
from django.test.testcases import TestCase
from django.test.utils import override_settings
from django.utils.translation import gettext_lazy as _

from import_export.admin import ImportExportMixin


class ImportTemplateTests(AdminTestMixin, TestCase):

    def test_import_export_template(self):
        response = self._get_url_response(self.core_book_url)
        self.assertTemplateUsed(response, self.change_list_template_url)
        self.assertTemplateUsed(response, self.change_list_url)
        self.assertTemplateUsed(response, self.change_list_url)
        self.assertContains(response, _("Import"))
        self.assertContains(response, _("Export"))
        self.assertContains(response, "Custom change list item")

    def test_issue_2205_change_list_template_as_property(self):
        # Third party mixins (e.g. django-admin-sortable2) may declare
        # change_list_template as a read-only property returning a list of
        # candidate templates.  The import / export links must still render,
        # and our template must extend the first template which exists.
        class SortableLikeAdmin(ImportExportMixin, ModelAdmin):
            @property
            def change_list_template(self):
                return ["does/not/exist.html", "core/admin/change_list.html"]

        model_admin = SortableLikeAdmin(Book, admin.site)
        request = RequestFactory().get(self.core_book_url)
        request.user = self.user
        response = model_admin.changelist_view(request)
        response.render()

        self.assertEqual(response.template_name, self.change_list_template_url)
        self.assertEqual(
            response.context_data["ie_base_change_list_template"],
            "core/admin/change_list.html",
        )
        self.assertContains(response, _("Import"))
        self.assertContains(response, _("Export"))
        self.assertContains(response, "Custom change list item")

    def test_issue_2205_change_list_template_as_property_no_match(self):
        class BrokenAdmin(ImportExportMixin, ModelAdmin):
            @property
            def change_list_template(self):
                return ["does/not/exist.html"]

        model_admin = BrokenAdmin(Book, admin.site)
        request = RequestFactory().get(self.core_book_url)
        request.user = self.user
        with self.assertRaises(TemplateDoesNotExist):
            model_admin.changelist_view(request).render()

    def test_issue_2205_pre_v5_workaround_template_ignored(self):
        # The pre-v5 workaround for django-admin-sortable2 pointed
        # change_list_template at our own template.  This must not make our
        # template extend itself: fall back to Django's defaults.
        class WorkaroundAdmin(ImportExportMixin, ModelAdmin):
            change_list_template = "admin/import_export/change_list_import_export.html"

        model_admin = WorkaroundAdmin(Book, admin.site)
        request = RequestFactory().get(self.core_book_url)
        request.user = self.user
        response = model_admin.changelist_view(request)
        response.render()

        self.assertEqual(response.template_name, self.change_list_template_url)
        self.assertEqual(
            response.context_data["ie_base_change_list_template"],
            "admin/change_list.html",
        )
        self.assertContains(response, _("Import"))
        self.assertContains(response, _("Export"))

    def test_issue_2205_other_template_response_not_replaced(self):
        # A mixin which returns a TemplateResponse without the ChangeList in
        # its context from changelist_view() must be left alone.
        class OtherResponseMixin:
            def changelist_view(self, request, extra_context=None):
                return TemplateResponse(request, "core/admin/change_list.html")

        class OtherResponseAdmin(ImportExportMixin, OtherResponseMixin, ModelAdmin):
            pass

        model_admin = OtherResponseAdmin(Book, admin.site)
        request = RequestFactory().get(self.core_book_url)
        request.user = self.user
        response = model_admin.changelist_view(request)

        self.assertEqual(response.template_name, "core/admin/change_list.html")
        self.assertIsNone(response.context_data)

    def test_issue_2205_action_response_not_replaced(self):
        # Admin actions may return their own TemplateResponse from
        # changelist_view (e.g. the delete confirmation page).  These must not
        # be swapped for the import / export change list template.
        book = Book.objects.create(name="Some book")
        data = {
            "action": "delete_selected",
            "_selected_action": [str(book.id)],
        }
        response = self._post_url_response(self.core_book_url, data)
        self.assertTemplateUsed(response, "admin/delete_selected_confirmation.html")
        self.assertTemplateNotUsed(response, self.change_list_template_url)

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
            self._prepend_form_prefix(data)
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
        self._prepend_form_prefix(data)
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
