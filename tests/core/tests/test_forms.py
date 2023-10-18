from django.test import TestCase

from import_export import forms, resources


class MyResource(resources.ModelResource):
    class Meta:
        name = "My super resource"


class FormTest(TestCase):
    def test_formbase_init_blank_resources(self):
        resource_list = []
        form = forms.ImportExportFormBase(resources=resource_list)
        self.assertTrue("resource" not in form.fields)

    def test_formbase_init_one_resources(self):
        resource_list = [resources.ModelResource]
        form = forms.ImportExportFormBase(resources=resource_list)
        self.assertTrue("resource" not in form.fields)

    def test_formbase_init_two_resources(self):
        resource_list = [resources.ModelResource, MyResource]
        form = forms.ImportExportFormBase(resources=resource_list)
        self.assertEqual(
            form.fields["resource"].choices,
            [(0, "ModelResource"), (1, "My super resource")],
        )
