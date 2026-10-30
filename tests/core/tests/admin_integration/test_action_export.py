import warnings
from datetime import date, datetime
from functools import partial
from unittest import mock, skipUnless
from unittest.mock import MagicMock, PropertyMock, patch

from core.admin import CategoryAdmin
from core.models import Author, Book, Category, UUIDCategory
from core.tests.admin_integration.mixins import AdminTestMixin
from django import forms
from django.contrib import admin
from django.contrib.admin import AdminSite
from django.contrib.auth.models import User
from django.core.exceptions import (
    FieldError,
    ImproperlyConfigured,
    PermissionDenied,
)
from django.db import connection
from django.http import HttpRequest
from django.test import RequestFactory
from django.test.testcases import TestCase
from django.test.utils import CaptureQueriesContext, override_settings
from django.urls import reverse

from import_export.admin import ExportMixin
from import_export.forms import (
    ExportForm,
    ExportItemsField,
    ImportExportFormBase,
    SelectableFieldsExportForm,
)

try:
    from django.contrib.admin.options import ActionLocation
except ImportError:  # Django < 6.1
    ActionLocation = None


class NoItemsExportForm(SelectableFieldsExportForm):
    export_items = None


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
        self.uuid_resource_fields_payload = {
            "uuidcategoryresource_catid": True,
            "uuidcategoryresource_name": True,
        }
        self.named_author_resource_fields_payload = {
            "namedauthorresource_name": True,
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

    def _assert_category_queries_are_bounded(self, queries):
        table = Category._meta.db_table
        category_queries = [q["sql"] for q in queries if table in q["sql"]]
        self.assertTrue(category_queries)
        for sql in category_queries:
            self.assertIn(" IN (", sql)

    def _assert_export_items_rendered(self, response, pks):
        for pk in pks:
            self.assertContains(
                response,
                f'name="django-import-export-export_items" value="{pk}"',
                count=1,
            )

    def _post_export_items(self, export_items, url=None, fields=None):
        data = {
            "format": "0",
            "export_items": export_items,
            **(fields or self.resource_fields_payload),
        }
        self._prepend_form_prefix(data)
        return self._post_url_response(url or self.category_export_url, data)

    def _export_action_data(self, *objs):
        return {
            "action": ["export_admin_action"],
            "_selected_action": [str(obj.pk) for obj in objs],
        }

    @override_settings(IMPORT_EXPORT_SKIP_ADMIN_ACTION_EXPORT_UI=True)
    def test_export_skips_export_ui_page(self):
        data = {
            "action": ["export_admin_action"],
            "_selected_action": [str(self.cat1.id)],
        }
        response = self._post_url_response(self.category_change_url, data)
        self._check_export_response(response)

    @override_settings(IMPORT_EXPORT_SKIP_ADMIN_ACTION_EXPORT_UI=True)
    def test_export_skips_export_ui_page_FieldError(self):
        # issue 1723 - an export error on the skip-form action path must be
        # shown to the user instead of rendering the server error page
        with mock.patch("import_export.resources.Resource.export") as mock_export:
            mock_export.side_effect = FieldError("some unknown error")
            data = {
                "action": ["export_admin_action"],
                "_selected_action": [str(self.cat1.id)],
            }
            response = self._post_url_response(
                self.category_change_url, data, follow=True
            )
        self.assertIn("Some unknown error", response.content.decode())

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
        self._assert_export_items_rendered(response, [self.cat1.id])

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
        self._assert_export_items_rendered(response, [self.cat1.id, self.cat2.id])

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
        self._assert_export_items_rendered(response, [cat.pk])

    def test_export_post(self):
        # create a POST request with data selected from the 'action' export
        data = {
            "format": "0",
            "export_items": [str(self.cat1.id)],
            **self.resource_fields_payload,
        }
        self._prepend_form_prefix(data)
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
        # autospec so that Django's get_action() sees a function, not a MagicMock
        # which would answer any attribute lookup (e.g. 'locations')
        with mock.patch(
            "core.admin.CategoryAdmin.export_admin_action", autospec=True
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

    def test_export_admin_action_render_runs_no_changelist_filter_queries(self):
        # BookAdmin.list_filter has related filters, which query their related
        # tables when a ChangeList is built
        book = Book.objects.create(name="Book 1")
        change_url = reverse("admin:core_book_change", args=[book.id])
        tables = [
            connection.ops.quote_name(model._meta.db_table)
            for model in (Author, Category)
        ]
        with CaptureQueriesContext(connection) as queries:
            response = self._post_url_response(
                change_url, data={"_export-item": "Export", "name": book.name}
            )
        unbounded_queries = [
            q["sql"]
            for q in queries
            if any(table in q["sql"] for table in tables) and "WHERE" not in q["sql"]
        ]
        self.assertEqual([], unbounded_queries)
        export_items = response.context["form"].fields["export_items"]
        self.assertIs(Book, export_items.queryset.model)

    def test_export_admin_action_with_restricted_pks(self):
        data = {
            "format": "0",
            "export_items": [str(self.cat1.id)],
            **self.resource_fields_payload,
        }
        self._prepend_form_prefix(data)
        with mock.patch("core.admin.CategoryAdmin.get_queryset") as mock_get_queryset:
            mock_get_queryset.return_value = Category.objects.exclude(pk=self.cat1.pk)
            response = self._post_url_response(self.category_export_url, data)
            self.assertIn(
                "Select a valid choice. "
                f"{self.cat1.id} is not one of the available choices.",
                response.content.decode(),
            )

    def test_export_items_validation_query_is_bounded(self):
        data = {
            "export_items": [str(self.cat1.id)],
            **self.resource_fields_payload,
        }
        self._prepend_form_prefix(data)
        with CaptureQueriesContext(connection) as queries:
            response = self._post_url_response(self.category_export_url, data)
        self.assertEqual({"format"}, set(response.context["form"].errors))
        self._assert_category_queries_are_bounded(queries)

    def test_export_items_rejects_malformed_pk(self):
        pk = str(self.cat1.id)
        arabic_indic_pk = pk.translate(str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩"))
        not_a_choice = "Select a valid choice. {} is not one of the available choices."
        for export_items, message in [
            (["abc"], "“abc” is not a valid value."),
            (["²"], "“²” is not a valid value."),
            ([pk, "abc"], "“abc” is not a valid value."),
            (["99999999999999999999"], not_a_choice.format("99999999999999999999")),
            (["-99999999999999999999"], not_a_choice.format("-99999999999999999999")),
            *[
                ([value], not_a_choice.format(value))
                for value in [f" {pk}", f"+{pk}", f"0{pk}", arabic_indic_pk, f"{pk}\n"]
            ],
        ]:
            with self.subTest(export_items=export_items):
                response = self._post_export_items(export_items)
                self.assertFalse(response.has_header("Content-Disposition"))
                self.assertIn(message, response.content.decode())

    def test_export_post_with_custom_form_cleaning_export_items(self):
        cat2_pk = self.cat2.pk

        class ExcludingExportForm(SelectableFieldsExportForm):
            def clean_export_items(self):
                return self.cleaned_data["export_items"].exclude(pk=cat2_pk)

        with patch.object(
            CategoryAdmin, "get_export_form_class", return_value=ExcludingExportForm
        ):
            response = self._post_export_items([str(self.cat1.id), str(cat2_pk)])
        self._check_export_response(response)

    def test_export_post_custom_clean_export_items_stays_in_export_queryset(self):
        cat1, excluded = self.cat1, Category.objects.create(name="Excluded")

        class PkListExportForm(SelectableFieldsExportForm):
            def clean_export_items(self):
                return [str(cat1.pk), str(excluded.pk)]

        class NameListExportForm(SelectableFieldsExportForm):
            export_items = ExportItemsField(
                queryset=None,
                to_field_name="name",
                widget=forms.MultipleHiddenInput,
                required=False,
            )

            def clean_export_items(self):
                return [cat1.name, excluded.name]

        class InstanceListExportForm(SelectableFieldsExportForm):
            def clean_export_items(self):
                return [cat1, excluded]

        class FlatValuesListExportForm(SelectableFieldsExportForm):
            def clean_export_items(self):
                return Category.objects.filter(
                    pk__in=[cat1.pk, excluded.pk]
                ).values_list("pk", flat=True)

        class ValuesExportForm(SelectableFieldsExportForm):
            def clean_export_items(self):
                return Category.objects.filter(pk__in=[cat1.pk, excluded.pk]).values()

        class QuerySetExportForm(SelectableFieldsExportForm):
            def clean_export_items(self):
                return Category.objects.filter(pk__in=[cat1.pk, excluded.pk])

        class NameQuerySetExportForm(NameListExportForm):
            def clean_export_items(self):
                return Category.objects.filter(pk__in=[cat1.pk, excluded.pk])

        # a pk no Category has, so exporting the book's pk instead of the
        # categories it lists cannot pass by coincidence
        book = Book.objects.create(pk=10_000 + excluded.pk, name="Book 1")
        book.categories.add(cat1, excluded)

        class RelatedFlatValuesListExportForm(SelectableFieldsExportForm):
            def clean_export_items(self):
                return Book.objects.filter(pk=book.pk).values_list(
                    "categories", flat=True
                )

        for form_class, export_items in [
            (PkListExportForm, [str(self.cat1.pk), str(self.cat2.pk)]),
            (NameListExportForm, [self.cat1.name, self.cat2.name]),
            (InstanceListExportForm, [str(self.cat1.pk), str(self.cat2.pk)]),
            (FlatValuesListExportForm, [str(self.cat1.pk), str(self.cat2.pk)]),
            (ValuesExportForm, [str(self.cat1.pk), str(self.cat2.pk)]),
            (QuerySetExportForm, [str(self.cat1.pk), str(self.cat2.pk)]),
            (NameQuerySetExportForm, [self.cat1.name, self.cat2.name]),
            (RelatedFlatValuesListExportForm, [str(self.cat1.pk), str(self.cat2.pk)]),
        ]:
            with (
                self.subTest(form_class=form_class.__name__),
                patch.object(
                    CategoryAdmin, "get_export_form_class", return_value=form_class
                ),
                patch.object(
                    CategoryAdmin,
                    "get_queryset",
                    return_value=Category.objects.exclude(pk=excluded.pk),
                ),
            ):
                response = self._post_export_items(export_items)
                self.assertEqual(
                    f"id,name\r\n{cat1.pk},Cat 1\r\n".encode(), response.content
                )

    def test_export_action_passes_selection_to_form_init(self):
        initial_export_items = []

        class InitialInspectingExportForm(SelectableFieldsExportForm):
            def __init__(self, formats, resources, **kwargs):
                initial_export_items.append(
                    kwargs.get("initial", {}).get("export_items")
                )
                super().__init__(formats, resources, **kwargs)

        with patch.object(
            CategoryAdmin,
            "get_export_form_class",
            return_value=InitialInspectingExportForm,
        ):
            self._post_url_response(
                self.category_change_url, self._export_action_data(self.cat1)
            )
        self.assertEqual([[self.cat1.pk]], initial_export_items)

    def test_export_post_with_prefixed_form(self):
        data = {
            "format": "0",
            "export_items": [str(self.cat1.id)],
            **self.resource_fields_payload,
        }
        self._prepend_form_prefix(data)
        data = {f"p-{key}": value for key, value in data.items()}
        for base_form in [SelectableFieldsExportForm, NoItemsExportForm]:

            class PrefixedExportForm(base_form):
                prefix = "p"

            with self.subTest(base_form=base_form.__name__):
                with patch.object(
                    CategoryAdmin,
                    "get_export_form_class",
                    return_value=PrefixedExportForm,
                ):
                    response = self._post_url_response(self.category_export_url, data)
                self._check_export_response(response)

    def test_export_action_with_form_without_export_items(self):
        change_url = reverse("admin:core_category_change", args=[self.cat1.id])
        with patch.object(
            CategoryAdmin, "get_export_form_class", return_value=NoItemsExportForm
        ):
            for url, data in [
                (self.category_change_url, self._export_action_data(self.cat1)),
                (change_url, {"_export-item": "Export", "name": self.cat1.name}),
            ]:
                with self.subTest(url=url):
                    response = self._post_url_response(url, data)
                    self._assert_export_items_rendered(response, [self.cat1.id])
            response = self._post_export_items([str(self.cat1.id)])
        self._check_export_response(response)

    def test_export_post_without_export_items_field_fails_closed_without_queryset(
        self,
    ):
        with (
            patch.object(
                CategoryAdmin, "get_export_form_class", return_value=NoItemsExportForm
            ),
            patch.object(CategoryAdmin, "get_export_queryset", return_value=[]),
        ):
            with self.assertRaises(ImproperlyConfigured):
                self._post_export_items([str(self.cat1.id)])

    def test_export_post_ignores_field_queryset_without_export_queryset(self):
        class FieldQuerysetExportForm(SelectableFieldsExportForm):
            export_items = ExportItemsField(
                queryset=Category.objects.all(),
                widget=forms.MultipleHiddenInput,
                required=False,
            )

        with (
            patch.object(
                CategoryAdmin,
                "get_export_form_class",
                return_value=FieldQuerysetExportForm,
            ),
            patch.object(CategoryAdmin, "get_export_queryset", return_value=[]),
        ):
            with self.assertRaisesRegex(ImproperlyConfigured, "get_export_queryset"):
                self._post_export_items([str(self.cat1.id)])

    def test_export_with_form_not_subclassing_export_form(self):
        class BaseExportForm(ImportExportFormBase):
            pass

        with patch.object(
            CategoryAdmin, "get_export_form_class", return_value=BaseExportForm
        ):
            self._get_url_response(self.category_export_url)
            response = self._post_url_response(
                self.category_export_url, {"django-import-export-format": "0"}
            )
            self.assertContains(response, self.cat1.name)
            self.assertContains(response, self.cat2.name)
            response = self._post_url_response(
                self.category_change_url, self._export_action_data(self.cat1)
            )
            self._assert_export_items_rendered(response, [self.cat1.id])
            response = self._post_export_items([str(self.cat1.id)])
        self._check_export_response(response)

    def test_export_with_form_class_that_is_not_a_class(self):
        with patch.object(
            CategoryAdmin,
            "get_export_form_class",
            return_value=partial(SelectableFieldsExportForm),
        ):
            response = self._post_url_response(
                self.category_change_url, self._export_action_data(self.cat1)
            )
            self._assert_export_items_rendered(response, [self.cat1.id])
            response = self._post_export_items([str(self.cat1.id)])
        self._check_export_response(response)

    def test_export_with_export_form_init_not_accepting_queryset(self):
        class WithoutKwargsExportForm(SelectableFieldsExportForm):
            def __init__(self, formats, resources, data=None, initial=None):
                super().__init__(formats, resources, data=data, initial=initial)

        # takes **kwargs but does not route them through ExportForm.__init__()
        class KwargsBypassingExportForm(ExportForm):
            def __init__(self, formats, resources, **kwargs):
                ImportExportFormBase.__init__(self, formats, resources, **kwargs)

        for form_class in [WithoutKwargsExportForm, KwargsBypassingExportForm]:
            with (
                self.subTest(form_class=form_class.__name__),
                patch.object(
                    CategoryAdmin, "get_export_form_class", return_value=form_class
                ),
            ):
                self._get_url_response(self.category_export_url)
                response = self._post_export_items([])
                self.assertContains(response, self.cat1.name)
                self.assertContains(response, self.cat2.name)
                response = self._post_url_response(
                    self.category_change_url, self._export_action_data(self.cat1)
                )
                self._assert_export_items_rendered(response, [self.cat1.id])
                response = self._post_export_items([str(self.cat1.id)])
                self._check_export_response(response)

    def test_export_with_base_form_declaring_another_export_items_field(self):
        # the v4 idiom for a form not built on ExportForm
        class MultipleChoiceExportForm(ImportExportFormBase):
            export_items = forms.MultipleChoiceField(
                widget=forms.MultipleHiddenInput, required=False
            )

        with patch.object(
            CategoryAdmin,
            "get_export_form_class",
            return_value=MultipleChoiceExportForm,
        ):
            with self.assertRaisesRegex(ImproperlyConfigured, "ExportItemsField"):
                self._post_url_response(
                    self.category_change_url, self._export_action_data(self.cat1)
                )
            with self.assertRaisesRegex(ImproperlyConfigured, "ExportItemsField"):
                self._post_export_items([str(self.cat1.id)])

    def test_export_with_export_form_subclass_declaring_another_export_items_field(
        self,
    ):
        class MultipleChoiceExportForm(SelectableFieldsExportForm):
            export_items = forms.MultipleChoiceField(
                widget=forms.MultipleHiddenInput, required=False
            )

        with (
            patch.object(
                CategoryAdmin,
                "get_export_form_class",
                return_value=MultipleChoiceExportForm,
            ),
            patch.object(CategoryAdmin, "get_export_queryset", return_value=[]),
        ):
            with self.assertRaisesRegex(ImproperlyConfigured, "ExportItemsField"):
                self._post_export_items([str(self.cat1.id)])

    def test_export_action_with_export_items_to_field_name(self):
        class NameKeyedExportForm(SelectableFieldsExportForm):
            export_items = ExportItemsField(
                queryset=None,
                to_field_name="name",
                widget=forms.MultipleHiddenInput,
                required=False,
            )

        change_url = reverse("admin:core_category_change", args=[self.cat1.id])
        with patch.object(
            CategoryAdmin, "get_export_form_class", return_value=NameKeyedExportForm
        ):
            for url, data in [
                (self.category_change_url, self._export_action_data(self.cat1)),
                (change_url, {"_export-item": "Export", "name": self.cat1.name}),
            ]:
                with self.subTest(url=url):
                    response = self._post_url_response(url, data)
                    self._assert_export_items_rendered(response, [self.cat1.name])
                    rendered = response.context["form"]["export_items"].value()
                    response = self._post_export_items(rendered)
                    self._check_export_response(response)

    def test_export_post_model_with_custom_PK(self):
        cat = UUIDCategory.objects.create(name="UUIDCategory 1")
        UUIDCategory.objects.create(name="UUIDCategory 2")
        response = self._post_export_items(
            [str(cat.pk)],
            url=self.uuid_category_export_url,
            fields=self.uuid_resource_fields_payload,
        )
        self.assertEqual(response["Content-Type"], "text/csv")
        target_str = f"catid,name\r\n{cat.pk},UUIDCategory 1\r\n"
        self.assertEqual(target_str.encode(), response.content)

    def test_export_items_rejects_malformed_uuid_pk(self):
        response = self._post_export_items(
            ["abc"],
            url=self.uuid_category_export_url,
            fields=self.uuid_resource_fields_payload,
        )
        self.assertIn("“abc” is not a valid value.", response.content.decode())

    def test_export_items_rejects_pk_with_null_character(self):
        response = self._post_export_items(
            ["a\x00"],
            url=self.named_author_export_url,
            fields=self.named_author_resource_fields_payload,
        )
        self.assertFalse(response.has_header("Content-Disposition"))
        self.assertIn("Null characters are not allowed.", response.content.decode())

    def _perform_export_action_calls_modeladmin_get_queryset_test(
        self, data, expected_pks
    ):
        # Issue #1864
        # ModelAdmin's get_queryset should be used in the ModelAdmin mixins
        with (
            mock.patch(
                "core.admin.CategoryAdmin.get_queryset",
                return_value=Category.objects.filter(pk=self.cat1.pk),
            ) as mock_modeladmin_get_queryset,
            mock.patch(
                "import_export.admin.ExportMixin.get_data_for_export"
            ) as mock_get_data_for_export,
        ):
            self._post_url_response(self.category_export_url, data)

            mock_modeladmin_get_queryset.assert_called()
            mock_get_data_for_export.assert_called()

            queryset = mock_get_data_for_export.call_args[0][1]
            self.assertIs(Category, queryset.model)
            self.assertCountEqual(expected_pks, [obj.pk for obj in queryset])

    def test_export_action_calls_modeladmin_get_queryset(self):
        # Issue #1864
        # Test with specific export items

        data = {
            "format": "0",
            "export_items": [str(self.cat1.id)],
            **self.resource_fields_payload,
        }
        self._prepend_form_prefix(data)
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            self._perform_export_action_calls_modeladmin_get_queryset_test(
                data, [self.cat1.pk]
            )

    def test_export_action_calls_modeladmin_get_queryset_all_items(self):
        # Issue #1864
        # Test without specific export items

        data = {
            "format": "0",
            **self.resource_fields_payload,
        }
        self._prepend_form_prefix(data)
        self._perform_export_action_calls_modeladmin_get_queryset_test(
            data, [self.cat1.pk]
        )

    def test_export_action_calls_modeladmin_get_queryset_rejects_other_items(self):
        # Issue #1864
        data = {
            "format": "0",
            "export_items": [str(self.cat1.id), str(self.cat2.id)],
            **self.resource_fields_payload,
        }
        self._prepend_form_prefix(data)
        with (
            mock.patch(
                "core.admin.CategoryAdmin.get_queryset",
                return_value=Category.objects.filter(pk=self.cat1.pk),
            ),
            mock.patch(
                "import_export.admin.ExportMixin.get_data_for_export"
            ) as mock_get_data_for_export,
        ):
            response = self._post_url_response(self.category_export_url, data)
        mock_get_data_for_export.assert_not_called()
        self.assertIn(
            "Select a valid choice. "
            f"{self.cat2.id} is not one of the available choices.",
            response.content.decode(),
        )

    @override_settings(IMPORT_EXPORT_SKIP_ADMIN_EXPORT_UI=True)
    def test_export_action_calls_modeladmin_get_queryset_skip_export_ui(self):
        # Issue #1864
        # Test with specific export items and skip UI
        # a POST from the action export form is processed as a form submission
        # even when the skip export UI setting is enabled (issue #1723)

        data = {
            "format": "0",
            "export_items": [str(self.cat1.id)],
            **self.resource_fields_payload,
        }
        self._prepend_form_prefix(data)
        self._perform_export_action_calls_modeladmin_get_queryset_test(
            data, [self.cat1.pk]
        )

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

    def test_export_with_get_export_queryset_returning_a_list(self):
        with patch.object(
            CategoryAdmin, "get_export_queryset", return_value=[self.cat1]
        ):
            self._get_url_response(self.category_export_url)
            self._check_export_response(self._post_export_items([]))
            with self.assertRaisesRegex(ImproperlyConfigured, "get_export_queryset"):
                self._post_export_items([str(self.cat1.id)])


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

    def test_export_items_rejects_pk_outside_filtered_changelist(self):
        data = {
            "format": "0",
            "export_items": [str(self.new_book1.id)],
            **self.resource_fields_payload,
        }
        self._prepend_form_prefix(data)
        response = self._post_url_response(
            self.book_export_url + "?birthday=before", data
        )
        self.assertIn(
            "Select a valid choice. "
            f"{self.new_book1.id} is not one of the available choices.",
            response.content.decode(),
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
        self._prepend_form_prefix(export_data)

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

    @override_settings(IMPORT_EXPORT_SKIP_ADMIN_ACTION_EXPORT_UI=True)
    def test_export_button_on_change_form_skip_form_FieldError(self):
        # issue 1723 - an export error on the change form export must redirect
        # back to the change form with the error shown, not raise a server error
        with mock.patch("import_export.resources.Resource.export") as mock_export:
            mock_export.side_effect = FieldError("some unknown error")
            response = self._post_url_response(
                self.change_url,
                data={"_export-item": "Export", "name": self.cat1.name},
                follow=True,
            )
        self.assertEqual([(self.change_url, 302)], response.redirect_chain)
        self.assertIn("Some unknown error", response.content.decode())

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

    def test_skip_export_form_enabled(self):
        self.model_admin.skip_export_form = True
        response = self.model_admin.export_admin_action(self.request, self.queryset)
        target_file_contents = "id,name\r\n" f"{self.cat1.id},Cat 1\r\n"
        self.assertEqual(target_file_contents.encode(), response.content)

    @override_settings(IMPORT_EXPORT_SKIP_ADMIN_EXPORT_UI=True)
    def test_skip_export_form_setting_enabled(self):
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
        response = self._post_url_response(
            self.change_url, data={"_export-item": "Export", "name": self.cat1.name}
        )
        target_file_contents = "id,name\r\n" f"{self.cat1.id},Cat 1\r\n"
        self.assertEqual(target_file_contents.encode(), response.content)

    def test_export_button_on_change_form_skip_export_form_enabled(self):
        with patch(
            "core.admin.CategoryAdmin.skip_export_form",
            new_callable=PropertyMock,
            return_value=True,
        ):
            response = self._post_url_response(
                self.change_url, data={"_export-item": "Export", "name": self.cat1.name}
            )
            target_file_contents = "id,name\r\n" f"{self.cat1.id},Cat 1\r\n"
            self.assertEqual(target_file_contents.encode(), response.content)


class ExportActionGetActionsTest(AdminTestMixin, TestCase):
    """
    ``get_actions()`` must integrate with Django's action API, which gained an
    ``action_location`` parameter in Django 6.1.
    """

    def setUp(self):
        super().setUp()
        # the admin only renders the action form when there are results
        Category.objects.create(name="Cat 1")
        self.model_admin = CategoryAdmin(Category, AdminSite())
        self.request = RequestFactory().get(self.category_change_url)
        self.request.user = User.objects.create_superuser(
            "superuser", "superuser@example.com", "password"
        )

    def test_export_action_in_change_list_actions(self):
        actions = self.model_admin.get_actions(self.request)
        self.assertIn("export_admin_action", actions)

    def test_export_action_choice_description(self):
        choices = self.model_admin.get_action_choices(self.request)
        self.assertIn(("export_admin_action", "Export selected categories"), choices)

    @skipUnless(ActionLocation, "requires Django 6.1+")
    def test_export_action_in_change_list_location(self):
        actions = self.model_admin.get_actions(
            self.request, action_location=ActionLocation.CHANGE_LIST
        )
        self.assertIn("export_admin_action", actions)

    @skipUnless(ActionLocation, "requires Django 6.1+")
    def test_export_action_not_in_change_form_location(self):
        actions = self.model_admin.get_actions(
            self.request, action_location=ActionLocation.CHANGE_FORM
        )
        self.assertNotIn("export_admin_action", actions)

    @skipUnless(ActionLocation, "requires Django 6.1+")
    def test_change_list_does_not_emit_get_actions_deprecation_warning(self):
        with warnings.catch_warnings():
            warnings.simplefilter("error", DeprecationWarning)
            warnings.simplefilter("error", PendingDeprecationWarning)
            response = self.client.get(self.category_change_url)
        self.assertEqual(200, response.status_code)
        self.assertIn(
            '<option value="export_admin_action">Export selected categories</option>',
            response.content.decode(),
        )
