from unittest import mock

import django.forms
from core.models import Author, Category
from core.tests.admin_integration.mixins import AdminTestMixin
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import connection, models
from django.db.models.functions import Upper
from django.test import SimpleTestCase, TestCase
from django.test.utils import CaptureQueriesContext, isolate_apps

from import_export import constants, forms, resources
from import_export.formats.base_formats import CSV

from .resources import BookResource, BookResourceWithStoreInstance


class MyResource(resources.ModelResource):
    class Meta:
        name = "My super resource"


class FormTest(TestCase):
    def test_formbase_init_blank_resources(self):
        with self.assertRaises(ValueError):
            forms.ImportExportFormBase(["format1"], [])

    def test_formbase_init_one_resource(self):
        form = forms.ImportExportFormBase([CSV], [resources.ModelResource])
        self.assertEqual(
            form.fields["resource"].choices,
            [(0, "ModelResource")],
        )
        self.assertEqual(form.initial["resource"], "0")
        self.assertIsInstance(
            form.fields["resource"].widget,
            django.forms.HiddenInput,
        )

    def test_formbase_init_two_resources(self):
        form = forms.ImportExportFormBase([CSV], [resources.ModelResource, MyResource])
        self.assertEqual(
            form.fields["resource"].choices,
            [(0, "ModelResource"), (1, "My super resource")],
        )
        self.assertNotIn("resource", form.initial)
        self.assertIsInstance(
            form.fields["resource"].widget,
            django.forms.Select,
        )

    def test_export_form_queryset_is_keyword_only(self):
        with self.assertRaises(TypeError):
            forms.ExportForm(
                [CSV],
                [resources.ModelResource],
                {f"{constants.FORM_FIELD_PREFIX}format": "0"},
            )

    def test_export_form_export_items_without_queryset(self):
        form = forms.ExportForm(
            [CSV],
            [resources.ModelResource],
            data={
                f"{constants.FORM_FIELD_PREFIX}format": "0",
                f"{constants.FORM_FIELD_PREFIX}export_items": ["1"],
            },
        )
        with self.assertRaisesRegex(ImproperlyConfigured, "queryset"):
            form.is_valid()

    def test_required_export_items_field_without_queryset_rejects_empty(self):
        field = forms.ExportItemsField(queryset=None, required=True)
        with self.assertRaises(django.forms.ValidationError) as cm:
            field.clean([])
        self.assertEqual("required", cm.exception.code)

    def test_export_form_export_items_without_queryset_or_selection(self):
        form = forms.ExportForm(
            [CSV],
            [resources.ModelResource],
            data={f"{constants.FORM_FIELD_PREFIX}format": "0"},
        )
        self.assertTrue(form.is_valid())
        self.assertEqual([], form.cleaned_data["export_items"])

    def test_export_form_without_export_items_field(self):
        class NoExportItemsForm(forms.ExportForm):
            export_items = None

        form = NoExportItemsForm(
            [CSV], [resources.ModelResource], queryset=Author.objects.all()
        )
        self.assertNotIn("export_items", form.fields)

    def test_export_form_export_items_requires_export_items_field(self):
        class MultipleChoiceExportForm(forms.ExportForm):
            export_items = django.forms.MultipleChoiceField(required=False)

        with self.assertRaisesRegex(ImproperlyConfigured, "ExportItemsField"):
            MultipleChoiceExportForm(
                [CSV], [resources.ModelResource], queryset=Author.objects.all()
            )

    def test_export_form_ignores_queryset_which_is_not_a_queryset(self):
        form = forms.ExportForm([CSV], [resources.ModelResource], queryset=[])
        self.assertIsNone(form.fields["export_items"].queryset)

    def test_export_form_ignores_class_queryset_when_queryset_is_not_a_queryset(self):
        class ClassQuerysetExportForm(forms.ExportForm):
            export_items = forms.ExportItemsField(
                queryset=Category.objects.all(), required=False
            )

        category = Category.objects.create(name="Cat 1")
        form = ClassQuerysetExportForm(
            [CSV],
            [resources.ModelResource],
            queryset=[],
            data={
                f"{constants.FORM_FIELD_PREFIX}format": "0",
                f"{constants.FORM_FIELD_PREFIX}export_items": [str(category.pk)],
            },
        )
        with self.assertRaisesRegex(ImproperlyConfigured, "get_export_queryset"):
            form.is_valid()

    def test_export_form_init_not_passing_queryset_names_the_cause(self):
        class DroppingExportForm(forms.ExportForm):
            def __init__(self, formats, resources, queryset=None, **kwargs):
                super().__init__(formats, resources, **kwargs)

        form = DroppingExportForm(
            [CSV],
            [resources.ModelResource],
            queryset=Category.objects.all(),
            data={
                f"{constants.FORM_FIELD_PREFIX}format": "0",
                f"{constants.FORM_FIELD_PREFIX}export_items": ["1"],
            },
        )
        with self.assertRaisesRegex(ImproperlyConfigured, r"super\(\)\.__init__\(\)"):
            form.is_valid()

    def test_export_items_field_reads_only_the_pk_column(self):
        category = Category.objects.create(name="Cat 1")
        field = forms.ExportItemsField(queryset=Category.objects.all())
        with CaptureQueriesContext(connection) as queries:
            field.clean([str(category.pk)])
        self.assertEqual(1, len(queries))
        self.assertNotIn(connection.ops.quote_name("name"), queries[0]["sql"])

    def test_export_items_field_char_to_field_name_skips_range_check(self):
        category = Category.objects.create(name="99999999999999999999")
        field = forms.ExportItemsField(
            queryset=Category.objects.all(), to_field_name="name"
        )
        self.assertEqual([category], list(field.clean([category.name])))

    def test_export_items_field_integer_to_field_name_checks_range(self):
        author = Author.objects.create(name="Author 1", resource=1)
        field = forms.ExportItemsField(
            queryset=Author.objects.all(), to_field_name="resource"
        )
        self.assertEqual([author], list(field.clean(["1"])))
        with self.assertRaises(ValidationError) as cm:
            field.clean(["99999999999999999999"])
        self.assertEqual("invalid_choice", cm.exception.code)

    def test_export_items_field_skips_unknown_integer_field_range(self):
        # an IntegerField subclass with a custom get_internal_type()
        category = Category.objects.create(name="Cat 1")
        field = forms.ExportItemsField(queryset=Category.objects.all())
        with mock.patch.object(
            connection.ops, "integer_field_range", side_effect=KeyError
        ):
            self.assertEqual([category], list(field.clean([str(category.pk)])))

    def test_export_items_field_to_field_name_pk(self):
        category = Category.objects.create(name="Cat 1")
        field = forms.ExportItemsField(
            queryset=Category.objects.all(), to_field_name="pk"
        )
        self.assertEqual([category], list(field.clean([str(category.pk)])))
        with self.assertRaises(ValidationError) as cm:
            field.clean(["99999999999999999999"])
        self.assertEqual("invalid_choice", cm.exception.code)

    def test_export_items_field_to_field_name_annotation(self):
        category = Category.objects.create(name="Cat 1")
        field = forms.ExportItemsField(
            queryset=Category.objects.annotate(upper_name=Upper("name")),
            to_field_name="upper_name",
        )
        self.assertEqual([category], list(field.clean(["CAT 1"])))

    def test_export_items_field_reports_invalid_pk_before_out_of_range(self):
        field = forms.ExportItemsField(queryset=Category.objects.all())
        with self.assertRaises(ValidationError) as cm:
            field.clean(["abc", "99999999999999999999"])
        self.assertEqual("invalid_pk_value", cm.exception.code)

    def test_export_items_field_to_python_rejects_out_of_range(self):
        field = forms.ExportItemsField(queryset=Category.objects.all())
        with self.assertRaises(ValidationError) as cm:
            field.to_python(["99999999999999999999"])
        self.assertEqual("invalid_choice", cm.exception.code)

    def test_export_items_field_accepts_range_bounds(self):
        category = Category.objects.create(name="Cat 1")
        field = forms.ExportItemsField(queryset=Category.objects.all())
        with mock.patch.object(
            connection.ops,
            "integer_field_range",
            return_value=(category.pk, category.pk),
        ):
            self.assertEqual([category], list(field.clean([str(category.pk)])))

    def test_export_items_field_rejects_none(self):
        field = forms.ExportItemsField(queryset=Category.objects.all())
        with self.assertRaises(ValidationError) as cm:
            field.clean([None])
        self.assertEqual("invalid_choice", cm.exception.code)


class ExportItemsFieldInheritedPkTest(SimpleTestCase):
    # no tables, the rejection runs no query
    @isolate_apps("core")
    def test_export_items_rejects_out_of_range_inherited_pk(self):
        class RangeParent(models.Model):
            class Meta:
                app_label = "core"

        class RangeChild(RangeParent):
            class Meta:
                app_label = "core"

        field = forms.ExportItemsField(queryset=RangeChild.objects.all())
        with self.assertRaises(ValidationError) as cm:
            field.clean(["99999999999999999999"])
        self.assertEqual("invalid_choice", cm.exception.code)


class ImportFormMediaTest(TestCase):
    def test_import_form_media(self):
        form = forms.ImportForm([CSV], [MyResource])
        media = form.media
        self.assertEqual(
            media._css,
            {},
        )
        self.assertEqual(
            media._js,
            [
                "admin/js/vendor/jquery/jquery.min.js",
                "admin/js/jquery.init.js",
                "import_export/guess_format.js",
            ],
        )

    def test_import_form_and_custom_widget_media(self):
        class TestMediaWidget(django.forms.TextInput):
            """Dummy test widget with associated CSS and JS media."""

            class Media:
                css = {
                    "all": ["test.css"],
                }
                js = ["test.js"]

        class CustomImportForm(forms.ImportForm):
            """Dummy custom import form with a custom widget."""

            author = django.forms.ModelChoiceField(
                queryset=Author.objects.none(),
                required=True,
                widget=TestMediaWidget,
            )

        form = CustomImportForm([CSV], [MyResource])
        media = form.media
        self.assertEqual(
            media._css,
            {"all": ["test.css"]},
        )
        self.assertEqual(
            media._js,
            [
                "test.js",
                "admin/js/vendor/jquery/jquery.min.js",
                "admin/js/jquery.init.js",
                "import_export/guess_format.js",
            ],
        )


class SelectableFieldsExportFormTest(AdminTestMixin, TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.resources = (BookResource, BookResourceWithStoreInstance)
        cls.form = forms.SelectableFieldsExportForm(
            formats=(CSV,),
            resources=cls.resources,
        )

    def test_create_boolean_fields(self) -> None:
        form_fields = self.form.fields

        for resource in self.resources:
            fields = resource().get_export_order()
            for field in fields:
                field_name = forms.SelectableFieldsExportForm.create_boolean_field_name(
                    resource, field
                )
                self.assertIn(field_name, form_fields)
                form_field = form_fields[field_name]
                self.assertIsInstance(form_field, django.forms.BooleanField)

    def test_form_raises_validation_error_when_no_resource_fields_are_selected(
        self,
    ) -> None:
        data = {"resource": "0", "format": "0", "bookresource_id": False}
        form = forms.SelectableFieldsExportForm(
            formats=(CSV,), resources=self.resources, data=data
        )
        self.assertFalse(form.is_valid())
        self.assertTrue("Select at least 1 field for" in form.errors.as_text())

    def test_remove_unselected_resource_fields_on_validation(self):
        data = {"resource": "0", "format": "0"}
        self._prepend_form_prefix(data)
        # Add all field values to form data for validation
        for resource in self.resources:
            for field in resource().get_export_order():
                data[
                    forms.SelectableFieldsExportForm.create_boolean_field_name(
                        resource, field
                    )
                ] = True

        form = forms.SelectableFieldsExportForm(
            formats=(CSV,), resources=self.resources, data=data
        )

        self.assertTrue(form.is_valid())

        selected_resource = self.resources[0]
        selected_resource_fields = selected_resource().get_export_order()
        not_selected_resource = self.resources[1]  # resource on index 0 was selected

        for field in not_selected_resource().get_export_order():
            # Only assert fields which doesn't exist in selected resource's fields
            if field not in selected_resource_fields:
                self.assertNotIn(field, form.cleaned_data)

    def test_normalize_resource_field_names(self) -> None:
        """
        Field names are combination of resource's name and field name.
        After validation, fields that belong to unselected resources are removed
        and resource name is removed from field names
        """

        data = {"resource": "0", "format": "0"}
        self._prepend_form_prefix(data)
        # Add all field values to form data for validation
        for resource in self.resources:
            for field in resource().get_export_order():
                data[
                    forms.SelectableFieldsExportForm.create_boolean_field_name(
                        resource, field
                    )
                ] = "on"

        form = forms.SelectableFieldsExportForm(
            formats=(CSV,), resources=self.resources, data=data
        )
        self.assertTrue(form.is_valid())
        selected_resource = self.resources[0]

        for field in selected_resource().get_export_order():
            self.assertIn(field, form.cleaned_data)

    def test_get_selected_resource_fields_without_validation_raises_validation_error(
        self,
    ) -> None:
        self.assertRaises(
            django.forms.ValidationError, self.form.get_selected_resource_export_fields
        )

    def test_get_field_label(self):
        """test SelectableFieldsExportForm._get_field_label"""
        form = forms.SelectableFieldsExportForm(
            formats=(CSV,), resources=(BookResource,)
        )
        resource = BookResource()
        self.assertEqual(
            form._get_field_label(resource, "bookresource_id"),
            "Bookresource Id",
        )
        self.assertEqual(
            form._get_field_label(resource, "published"), "Published (published_date)"
        )

    def test_get_selected_rerource_fields(self) -> None:
        data = {"resource": "0", "format": "0"}
        self._prepend_form_prefix(data)
        form = forms.SelectableFieldsExportForm(
            formats=(CSV,), resources=self.resources, data=data
        )
        for resource in self.resources:
            for field in resource().get_export_order():
                data[
                    forms.SelectableFieldsExportForm.create_boolean_field_name(
                        resource, field
                    )
                ] = "on"

        self.assertTrue(form.is_valid())
        selected_resource = self.resources[0]()

        self.assertEqual(
            form.get_selected_resource_export_fields(),
            list(selected_resource.get_export_order()),
        )

    def test_fields_order(self) -> None:
        form = forms.SelectableFieldsExportForm(
            formats=(CSV,), resources=(BookResource,)
        )

        self.assertEqual(
            list(form.fields.keys()),
            [
                "resource",
                "bookresource_id",
                "bookresource_name",
                "bookresource_author",
                "bookresource_author_email",
                "bookresource_published",
                "bookresource_published_time",
                "bookresource_price",
                "bookresource_added",
                "bookresource_categories",
                "format",
                "export_items",
            ],
        )

    def test_resource_boolean_field_attributes(self) -> None:
        for resource_index, resource in enumerate(self.resources):
            resource_fields = resource().get_export_order()
            initial_field_checked = False

            for resource_field in resource_fields:
                field_name = forms.SelectableFieldsExportForm.create_boolean_field_name(
                    resource, resource_field
                )
                form_field = self.form.fields[field_name]

                if not initial_field_checked:
                    self.assertTrue(form_field.initial_field)
                    initial_field_checked = True

                self.assertTrue(form_field.is_selectable_field)
                self.assertEqual(form_field.resource_name, resource.__name__)
                self.assertEqual(form_field.resource_index, resource_index)
                self.assertEqual(form_field.widget.attrs["resource-id"], resource_index)
