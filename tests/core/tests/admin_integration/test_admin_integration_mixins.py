from django.test.testcases import TestCase
from core.admin import  ImportMixin
from import_export.admin import (
    ExportMixin,
)

class TestImportMixinDeprecationWarnings(TestCase):
    class TestMixin(ImportMixin):
        """
        TestMixin is a subclass which mimics a
        class which the user may have created
        """

        def get_import_form(self):
            return super().get_import_form()

        def get_confirm_import_form(self):
            return super().get_confirm_import_form()

        def get_form_kwargs(self, form_class, **kwargs):
            return super().get_form_kwargs(form_class, **kwargs)

    def setUp(self):
        super().setUp()
        self.import_mixin = ImportMixin()

    def test_get_import_form_warning(self):
        target_msg = (
            "ImportMixin.get_import_form() is deprecated and will be removed "
            "in a future release. "
            "Please use get_import_form_class() instead."
        )
        with self.assertWarns(DeprecationWarning) as w:
            self.import_mixin.get_import_form()
            self.assertEqual(target_msg, str(w.warnings[0].message))

    def test_get_confirm_import_form_warning(self):
        target_msg = (
            "ImportMixin.get_confirm_import_form() is deprecated and will be removed "
            "in a future release. "
            "Please use get_confirm_form_class() instead."
        )
        with self.assertWarns(DeprecationWarning) as w:
            self.import_mixin.get_confirm_import_form()
            self.assertEqual(target_msg, str(w.warnings[0].message))

    def test_get_form_kwargs_warning(self):
        target_msg = (
            "ImportMixin.get_form_kwargs() is deprecated and will be removed in a "
            "future release. "
            "Please use get_import_form_kwargs() or get_confirm_form_kwargs() instead."
        )
        with self.assertWarns(DeprecationWarning) as w:
            self.import_mixin.get_form_kwargs(None)
            self.assertEqual(target_msg, str(w.warnings[0].message))

    def test_get_import_form_class_warning(self):
        self.import_mixin = self.TestMixin()
        target_msg = (
            "ImportMixin.get_import_form() is deprecated and will be removed in a "
            "future release. "
            "Please use the new 'import_form_class' attribute to specify a custom form "
            "class, "
            "or override the get_import_form_class() method if your requirements are "
            "more complex."
        )
        with self.assertWarns(DeprecationWarning) as w:
            self.import_mixin.get_import_form_class(None)
            self.assertEqual(target_msg, str(w.warnings[0].message))

    def test_get_confirm_form_class_warning(self):
        self.import_mixin = self.TestMixin()
        target_msg = (
            "ImportMixin.get_confirm_import_form() is deprecated and will be removed "
            "in a future release. "
            "Please use the new 'confirm_form_class' attribute to specify a custom "
            "form class, "
            "or override the get_confirm_form_class() method if your requirements "
            "are more complex."
        )
        with self.assertWarns(DeprecationWarning) as w:
            self.import_mixin.get_confirm_form_class(None)
            self.assertEqual(target_msg, str(w.warnings[0].message))

class TestExportMixinDeprecationWarnings(TestCase):
    class TestMixin(ExportMixin):
        """
        TestMixin is a subclass which mimics a
        class which the user may have created
        """

        def get_export_form(self):
            return super().get_export_form()

    def setUp(self):
        super().setUp()
        self.export_mixin = self.TestMixin()

    def test_get_export_form_warning(self):
        target_msg = (
            "ExportMixin.get_export_form() is deprecated and will "
            "be removed in a future release. Please use the new "
            "'export_form_class' attribute to specify a custom form "
            "class, or override the get_export_form_class() method if "
            "your requirements are more complex."
        )
        with self.assertWarns(DeprecationWarning) as w:
            self.export_mixin.get_export_form()
            self.assertEqual(target_msg, str(w.warnings[0].message))