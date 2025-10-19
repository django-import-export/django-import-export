import warnings
from datetime import date, datetime
from unittest import mock
from unittest.mock import MagicMock, PropertyMock, patch

from core.admin import CategoryAdmin
from core.models import Author, Book, Category, UUIDCategory
from core.tests.admin_integration.mixins import AdminTestMixin
from django.contrib import admin
from django.contrib.admin import AdminSite
from django.contrib.auth.models import User
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
            f'attachment; filename="Category-{date_str}.csv"',
        )

    @override_settings(IMPORT_EXPORT_SKIP_ADMIN_ACTION_EXPORT_UI=True)
    def test_export_skips_export_ui_page(self):
        data = {
            "action": ["export_admin_action"],
            "_selected_action": [str(self.cat1.id)],
        }
        response = self._post_url_response(self.category_change_url, data)
        self._check_export_response(response)

    def test_export_displays_ui_select_page(self):
        data = {
            "action": ["export_admin_action"],
            "_selected_action": [str(self.cat1.id)],
        }
        response = self._post_url_response(self.category_change_url, data)
        self.assertIn("form", response.context)
        export_form = response.context["form"]
        data = export_form.initial
        self.assertEqual([self.cat1.id], data["export_items"])
        self.assertIn("Export 1 selected item.", response.content.decode())

    def test_export_displays_ui_select_page_multiple_items(self):
        data = {
            "action": ["export_admin_action"],
            "_selected_action": [str(self.cat1.id), str(self.cat2.id)],
        }
        response = self._post_url_response(self.category_change_url, data)
        self.assertIn("form", response.context)
        export_form = response.context["form"]
        data = export_form.initial
        self.assertEqual(
            sorted([self.cat1.id, self.cat2.id]), sorted(data["export_items"])
        )
        self.assertIn("Export 2 selected items.", response.content.decode())

    def test_action_export_model_with_custom_PK(self):
        # issue 1800
        cat = UUIDCategory.objects.create(name="UUIDCategory")
        data = {
            "action": ["export_admin_action"],
            "_selected_action": [str(cat.pk)],
        }
        response = self._post_url_response(self.uuid_category_change_url, data)
        self.assertIn("form", response.context)
        export_form = response.context["form"]
        data = export_form.initial
        self.assertEqual([cat.pk], data["export_items"])
        self.assertIn("Export 1 selected item.", response.content.decode())

    def test_export_post(self):
        # create a POST request with data selected from the 'action' export
        data = {
            "format": "0",
            "export_items": [str(self.cat1.id)],
            **self.resource_fields_payload,
        }
        date_str = datetime.now().strftime("%Y-%m-%d")
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            response = self._post_url_response(self.category_export_url, data)
        self.assertTrue(response.has_header("Content-Disposition"))
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertEqual(
            response["Content-Disposition"],
            f'attachment; filename="Category-{date_str}.csv"',
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

    def test_export_admin_action_with_restricted_pks(self):
        data = {
            "format": "0",
            "export_items": [str(self.cat1.id)],
            **self.resource_fields_payload,
        }
        # mock returning a set of pks which is not in the submitted range
        with mock.patch(
            "import_export.admin.ExportMixin.get_valid_export_item_pks"
        ) as mock_valid_pks:
            mock_valid_pks.return_value = [999]
            response = self._post_url_response(self.category_export_url, data)
            self.assertIn(
                "Select a valid choice. "
                f"{self.cat1.id} is not one of the available choices.",
                response.content.decode(),
            )

    def test_export_admin_action_with_restricted_pks_deprecated(self):
        data = {
            "format": "0",
            "export_items": [str(self.cat1.id)],
            **self.resource_fields_payload,
        }
        with self.assertWarnsRegex(
            DeprecationWarning,
            r"The 'get_valid_export_item_pks\(\)' method in "
            "core.admin.CategoryAdmin is deprecated and will be removed "
            "in a future release",
        ):
            self._post_url_response(self.category_export_url, data)

    def _perform_export_action_calls_modeladmin_get_queryset_test(self, data):
        # Issue #1864
        # ModelAdmin's get_queryset should be used in the ModelAdmin mixins
        with (
            mock.patch(
                "core.admin.CategoryAdmin.get_queryset"
            ) as mock_modeladmin_get_queryset,
            mock.patch(
                "import_export.admin.ExportMixin.get_data_for_export"
            ) as mock_get_data_for_export,
        ):
            mock_queryset = mock.MagicMock(name="MockQuerySet")
            mock_queryset.filter.return_value = mock_queryset
            mock_queryset.order_by.return_value = mock_queryset

            mock_modeladmin_get_queryset.return_value = mock_queryset

            self._post_url_response(self.category_export_url, data)

            mock_modeladmin_get_queryset.assert_called()
            mock_get_data_for_export.assert_called()

            args, kwargs = mock_get_data_for_export.call_args
            mock_get_data_for_export.assert_called_with(
                args[0], mock_queryset, **kwargs
            )

    def test_export_action_calls_modeladmin_get_queryset(self):
        # Issue #1864
        # Test with specific export items

        data = {
            "format": "0",
            "export_items": [str(self.cat1.id)],
            **self.resource_fields_payload,
        }
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            self._perform_export_action_calls_modeladmin_get_queryset_test(data)

    def test_export_action_calls_modeladmin_get_queryset_all_items(self):
        # Issue #1864
        # Test without specific export items

        data = {
            "format": "0",
            **self.resource_fields_payload,
        }
        self._perform_export_action_calls_modeladmin_get_queryset_test(data)

    @override_settings(IMPORT_EXPORT_SKIP_ADMIN_EXPORT_UI=True)
    def test_export_action_calls_modeladmin_get_queryset_skip_export_ui(self):
        # Issue #1864
        # Test with specific export items and skip UI

        data = {
            "format": "0",
            "export_items": [str(self.cat1.id)],
            **self.resource_fields_payload,
        }
        self._perform_export_action_calls_modeladmin_get_queryset_test(data)

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


class TestExportFilterPreservation(AdminTestMixin, TestCase):
    """
    Test cases for issue #2097: Admin filters are lost during export actions.

    Tests that admin changelist filters are properly preserved when exporting
    selected items through the export action using the AuthorBirthdayListFilter.
    """

    def setUp(self):
        super().setUp()

        # Create authors from different eras to test the AuthorBirthdayListFilter
        self.old_author1 = Author.objects.create(
            name="Old Author 1", birthday=date(1850, 1, 1)
        )
        self.old_author2 = Author.objects.create(
            name="Old Author 2", birthday=date(1880, 6, 15)
        )
        self.new_author1 = Author.objects.create(
            name="New Author 1", birthday=date(1950, 3, 10)
        )
        self.new_author2 = Author.objects.create(
            name="New Author 2", birthday=date(1970, 12, 25)
        )

        # Create books with authors from different eras
        self.old_book1 = Book.objects.create(name="Old Book 1", author=self.old_author1)
        self.old_book2 = Book.objects.create(name="Old Book 2", author=self.old_author2)
        self.new_book1 = Book.objects.create(name="New Book 1", author=self.new_author1)
        self.new_book2 = Book.objects.create(name="New Book 2", author=self.new_author2)

        # fields payload for `BookResource` - for `SelectableFieldsExportForm`
        self.resource_fields_payload = {
            "bookresource_id": True,
            "bookresource_name": True,
            "bookresource_author": True,
        }

    def test_export_action_preserves_admin_filters(self):
        """
        Test that admin filters are preserved when exporting selected items.
        This reproduces issue #2097 where applied filters are lost during export.

        Uses the AuthorBirthdayListFilter to test filter preservation with books.
        The issue occurs when:
        1. User applies filters in admin changelist (authors born before 1900)
        2. User selects items from filtered results
        3. User chooses "Export selected items" action
        4. The export URL loses the filter context, causing unfiltered export
        """
        # Step 1: Simulate POST action with AuthorBirthdayListFilter applied
        data = {
            "action": ["export_admin_action"],
            "_selected_action": [
                str(self.old_book1.id),
                str(self.old_book2.id),
            ],
        }

        # Add filter parameters to simulate applied admin filters
        filter_params = "?birthday=before"
        url_with_filters = self.core_book_url + filter_params

        # Make the request with filters applied
        response = self._post_url_response(url_with_filters, data)

        # Should get an export form
        self.assertIn("form", response.context)

        # Check that export_url preserves the filter parameters
        export_url = response.context.get("export_url", "")
        self.assertIn(
            "birthday=before",
            export_url,
            f"Export URL should preserve AuthorBirthdayListFilter parameters. "
            f"Got URL: '{export_url}'. Filter preservation is working!",
        )

    def test_export_action_filter_preservation_end_to_end(self):
        """
        Test the complete filter preservation workflow from action to final export.
        This test follows the complete flow: action -> form -> export with filters.
        """
        # Step 1: First trigger the export action with filters
        action_data = {
            "action": ["export_admin_action"],
            "_selected_action": [
                str(self.old_book1.id),
                str(self.old_book2.id),
            ],
        }

        # POST to changelist with filter to get export form
        filter_params = "?birthday=before"
        url_with_filters = self.core_book_url + filter_params
        action_response = self._post_url_response(url_with_filters, action_data)

        # Should get an export form with preserved filter URL
        self.assertIn("form", action_response.context)
        export_url = action_response.context.get("export_url", "")
        self.assertIn("birthday=before", export_url)

        # Step 2: Now submit the export form to the preserved URL
        export_data = {
            "format": "0",
            "export_items": [str(self.old_book1.id), str(self.old_book2.id)],
            **self.resource_fields_payload,
        }

        # POST to the export URL that should have preserved filters
        # Suppress the deprecation warning for get_valid_export_item_pks
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message=r"The 'get_valid_export_item_pks\(\)' method",
                category=DeprecationWarning,
            )
            final_response = self._post_url_response(export_url, export_data)

        # Should get CSV export that respects the filter context
        self.assertEqual(final_response["Content-Type"], "text/csv")
        content = final_response.content.decode()

        # Verify the export contains the expected filtered data
        lines = content.strip().split("\n")
        if len(lines) > 1:
            data_lines = lines[1:]  # Remove header
            # Should only contain the 2 selected books
            self.assertEqual(
                len(data_lines),
                2,
                f"Filter preservation working! Expected 2 books, got {len(data_lines)}",
            )


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
        self._get_url_response(self.change_url, str_in_response=self.target_str)
        response = self._post_url_response(
            self.change_url, data={"_export-item": "Export", "name": self.cat1.name}
        )
        self.assertIn("Export 1 selected item", response.content.decode())

    def test_export_button_on_change_form_for_custom_pk(self):
        self.cat1 = UUIDCategory.objects.create(name="Cat 1")
        self.change_url = reverse(
            "%s:%s_%s_change"
            % (
                "admin",
                "core",
                "uuidcategory",
            ),
            args=[self.cat1.pk],
        )
        response = self.client.get(self.change_url)
        self.assertIn(self.target_str, response.content.decode())
        response = self._post_url_response(
            self.change_url, data={"_export-item": "Export", "name": self.cat1.name}
        )
        self.assertIn("Export 1 selected item", response.content.decode())

    def test_save_button_on_change_form(self):
        # test default behavior is retained when saving an instance ChangeForm
        response = self._post_url_response(
            self.change_url, data={"_save": "Save", "name": self.cat1.name}, follow=True
        )
        target_str = f"The category.*{self.cat1.name}.*was changed successfully."
        self.assertRegex(response.content.decode(), target_str)

    def test_export_button_on_change_form_disabled(self):
        class MockCategoryAdmin(CategoryAdmin):
            show_change_form_export = True

        factory = RequestFactory()
        category_admin = MockCategoryAdmin(Category, admin.site)

        request = factory.get(self.change_url)
        request.user = self.user

        response = category_admin.change_view(request, str(self.cat1.id))
        response.render()

        self.assertIn(self.target_str, response.content.decode())

        category_admin.show_change_form_export = False
        response = category_admin.change_view(request, str(self.cat1.id))
        response.render()
        self.assertNotIn(self.target_str, response.content.decode())


class TestSkipExportFormFromAction(AdminTestMixin, TestCase):
    """
    Test config values when export is initiated from the 'Export' action in the action
    menu.
    """

    def setUp(self):
        super().setUp()
        self.cat1 = Category.objects.create(name="Cat 1")
        self.queryset = Category.objects.all()
        self.model_admin = CategoryAdmin(Category, AdminSite())

        factory = RequestFactory()
        data = {
            "action": ["export_admin_action"],
            "_selected_action": [str(self.cat1.id)],
        }
        self.request = factory.post(self.category_change_url, data=data)
        self.request.user = User.objects.create_user("admin1")

    def test_skip_export_form_from_action_enabled(self):
        self.model_admin.skip_export_form_from_action = True
        response = self.model_admin.export_admin_action(self.request, self.queryset)
        target_file_contents = "id,name\r\n" f"{self.cat1.id},Cat 1\r\n"
        self.assertEqual(target_file_contents.encode(), response.content)

    @override_settings(IMPORT_EXPORT_SKIP_ADMIN_ACTION_EXPORT_UI=True)
    def test_skip_export_form_from_action_setting_enabled(self):
        response = self.model_admin.export_admin_action(self.request, self.queryset)
        target_file_contents = "id,name\r\n" f"{self.cat1.id},Cat 1\r\n"
        self.assertEqual(target_file_contents.encode(), response.content)


class TestSkipExportFormFromChangeForm(AdminTestMixin, TestCase):
    """
    Test config values when export is initiated from the 'Export' button on the Change
    form.
    """

    def setUp(self):
        super().setUp()
        self.cat1 = Category.objects.create(name="Cat 1")
        self.queryset = Category.objects.all()
        self.model_admin = CategoryAdmin(Category, AdminSite())

        self.change_url = reverse(
            "%s:%s_%s_change"
            % (
                "admin",
                "core",
                "category",
            ),
            args=[self.cat1.id],
        )
        factory = RequestFactory()
        self.request = factory.post(
            self.change_url, data={"_export-item": "Export", "name": self.cat1.name}
        )
        self.request.user = User.objects.create_user("admin1")

    def test_export_button_on_change_form_skip_export_form_from_action_enabled(self):
        self.model_admin.skip_export_form_from_action = True
        response = self.model_admin.export_admin_action(self.request, self.queryset)
        target_file_contents = "id,name\r\n" f"{self.cat1.id},Cat 1\r\n"
        self.assertEqual(target_file_contents.encode(), response.content)

    @override_settings(IMPORT_EXPORT_SKIP_ADMIN_ACTION_EXPORT_UI=True)
    def test_export_button_on_change_form_skip_export_form_from_action_setting_enabled(
        self,
    ):
        self.model_admin.skip_export_form_from_action = True
        response = self.model_admin.export_admin_action(self.request, self.queryset)
        target_file_contents = "id,name\r\n" f"{self.cat1.id},Cat 1\r\n"
        self.assertEqual(target_file_contents.encode(), response.content)

    @override_settings(IMPORT_EXPORT_SKIP_ADMIN_EXPORT_UI=True)
    def test_export_button_on_change_form_skip_export_setting_enabled(self):
        # this property has no effect - IMPORT_EXPORT_SKIP_ADMIN_ACTION_EXPORT_UI
        # should be set instead
        response = self._post_url_response(
            self.change_url, data={"_export-item": "Export", "name": self.cat1.name}
        )
        target_re = r"This exporter will export the following fields:"
        self.assertRegex(response.content.decode(), target_re)

    def test_export_button_on_change_form_skip_export_form_enabled(self):
        # this property has no effect - skip_export_form_from_action
        # should be set instead
        with patch(
            "core.admin.CategoryAdmin.skip_export_form",
            new_callable=PropertyMock,
            return_value=True,
        ):
            response = self._post_url_response(
                self.change_url, data={"_export-item": "Export", "name": self.cat1.name}
            )
            target_re = r"This exporter will export the following fields:"
            self.assertRegex(response.content.decode(), target_re)
