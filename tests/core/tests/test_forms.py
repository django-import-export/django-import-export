from django.test import TestCase

from import_export import forms, resources
from import_export.formats.base_formats import CSV


class MyResource(resources.ModelResource):
    class Meta:
        name = "My super resource"


class FormTest(TestCase):
    def test_formbase_init_blank_resources(self):
        with self.assertRaises(ValueError):
            forms.ImportExportFormBase(["format1"], [])

    def test_formbase_init_one_resource(self):
        resource_list = [resources.ModelResource]
        form = forms.ImportExportFormBase([CSV], resource_list)
        self.assertTrue("resource" in form.fields)
        self.assertEqual("ModelResource", form.fields["resource"].value)
        self.assertTrue(form.fields["resource"].widget.attrs["readonly"])

    def test_formbase_init_two_resources(self):
        resource_list = [resources.ModelResource, MyResource]
        form = forms.ImportExportFormBase([CSV], resource_list)
        self.assertEqual(
            form.fields["resource"].choices,
            [(0, "ModelResource"), (1, "My super resource")],
        )
