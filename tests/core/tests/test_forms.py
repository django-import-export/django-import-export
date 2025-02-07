import django.forms
from core.models import Author
from django.test import TestCase

from import_export import forms, resources
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


class SelectableFieldsExportFormTest(TestCase):
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

    def test_get_selected_resrource_fields(self) -> None:
        data = {"resource": "0", "format": "0"}
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
