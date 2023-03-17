from django.test import TestCase

from core import admin
from import_export import forms, resources


class MyResource(resources.ModelResource):
    class Meta:
        name = "My super resource"


class FormTest(TestCase):

    def test_formbase_init_blank_resources(self):
        resource_list = []
        form = forms.ImportExportFormBase(resources=resource_list)
        self.assertTrue('resource' not in form.fields)

    def test_formbase_init_one_resources(self):
        resource_list = [resources.ModelResource]
        form = forms.ImportExportFormBase(resources=resource_list)
        self.assertTrue('resource' not in form.fields)

    def test_formbase_init_two_resources(self):
        resource_list = [resources.ModelResource, MyResource]
        form = forms.ImportExportFormBase(resources=resource_list)
        self.assertEqual(
            form.fields['resource'].choices,
            [(0, 'ModelResource'), (1, "My super resource")],
        )

    def test_resources_arg_deprecation_warning(self):
        class TestForm(forms.ImportExportFormBase):
            def __init__(self, *args, resources=None, **kwargs):
                self.args_ = args
                super().__init__(*args, resources=resources, **kwargs)

        resource_list = [resources.ModelResource, admin.BookResource]
        with self.assertWarns(DeprecationWarning) as w:
            f = TestForm(resource_list)
            self.assertEqual(
                "'resources' must be supplied as a named parameter",
                str(w.warnings[0].message)
            )
            self.assertEqual(f.args_, (resource_list, ))