from core.tests.admin_integration.mixins import AdminTestMixin
from django.contrib import admin
from django.contrib.admin.options import ModelAdmin
from django.contrib.auth.models import User
from django.test import RequestFactory
from django.test.testcases import TestCase

from import_export.admin import ImportExportMixinBase


class MockModelAdmin(ImportExportMixinBase, ModelAdmin):
    change_list_template = "admin/import_export/change_list.html"


class TestChangeListView(AdminTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()
        self.model_admin = MockModelAdmin(User, admin.site)

    def test_changelist_view_context(self):
        request = self.factory.get("/admin/")
        request.user = self.user

        # Call the changelist_view method
        self.model_admin.ie_base_change_list_template = None
        response = self.model_admin.changelist_view(request)

        # Render will throw an exception if the default for {% extends %} is not set
        response.render()

        # Check if the base_change_list_template context variable is set to None
        self.assertIsNone(response.context_data.get("base_change_list_template"))
        self.assertContains(
            response, '<a href="/admin/">Django administration</a>', html=True
        )
