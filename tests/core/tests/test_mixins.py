from unittest import mock
from unittest.mock import MagicMock

from core.models import Book
from core.tests.admin_integration.mixins import AdminTestMixin
from django.http import HttpRequest
from django.test.testcases import TestCase

from import_export import admin, forms, mixins, resources


class BaseImportMixinTest(TestCase):
    def test_get_import_formats(self):
        class Format:
            def __init__(self, id, can_import):
                self.id = id
                self.val = can_import

            def can_import(self):
                return self.val

        class CanImportFormat(Format):
            def __init__(self):
                super().__init__(1, True)

        class CannotImportFormat(Format):
            def __init__(self):
                super().__init__(2, False)

        class TestBaseImportMixin(mixins.BaseImportMixin):
            @property
            def import_formats(self):
                return [CanImportFormat, CannotImportFormat]

        m = TestBaseImportMixin()

        formats = m.get_import_formats()
        self.assertEqual(1, len(formats))
        self.assertEqual("CanImportFormat", formats[0].__name__)


class FooResource(resources.Resource):
    pass


class MixinModelAdminTest(AdminTestMixin, TestCase):
    """
    Tests for regression where methods in ModelAdmin with
    BaseImportMixin / BaseExportMixin do not get called.
    see #1315.
    """

    request = MagicMock(spec=HttpRequest)

    class BaseImportModelAdminTest(mixins.BaseImportMixin):
        call_count = 0

        def get_resource_classes(self, request, **kwargs):
            self.call_count += 1

        def get_resource_kwargs(self, request, **kwargs):
            self.call_count += 1

    class BaseExportModelAdminTest(mixins.BaseExportMixin):
        call_count = 0

        def get_resource_classes(self, request, **kwargs):
            self.call_count += 1

        def get_export_resource_kwargs(self, request, **kwargs):
            self.call_count += 1

    def test_get_import_resource_class_calls_self_get_resource_class(self):
        admin = self.BaseImportModelAdminTest()
        admin.get_import_resource_classes(self.request)
        self.assertEqual(1, admin.call_count)

    def test_get_import_resource_kwargs_calls_self_get_resource_kwargs(self):
        admin = self.BaseImportModelAdminTest()
        admin.get_import_resource_kwargs(self.request)
        self.assertEqual(1, admin.call_count)

    def test_get_export_resource_class_calls_self_get_resource_class(self):
        admin = self.BaseExportModelAdminTest()
        admin.get_export_resource_classes(self.request)
        self.assertEqual(1, admin.call_count)

    def test_get_export_resource_kwargs_calls_self_get_resource_kwargs(self):
        admin = self.BaseExportModelAdminTest()
        admin.get_export_resource_kwargs(self.request)
        self.assertEqual(1, admin.call_count)

    class BaseModelAdminFaultyResourceClassesTest(mixins.BaseExportMixin):
        resource_classes = resources.Resource

    def test_faulty_resource_class_raises_exception(self):
        """Test fallback mechanism to old get_export_resource_class() method"""
        admin = self.BaseModelAdminFaultyResourceClassesTest()
        with self.assertRaisesRegex(
            Exception, r"^The resource_classes field type must be subscriptable"
        ):
            admin.get_export_resource_classes(self.request)

    class BaseModelExportChooseTest(AdminTestMixin, mixins.BaseExportMixin):
        resource_classes = [resources.Resource, FooResource]

    @mock.patch("import_export.admin.SelectableFieldsExportForm")
    def test_choose_export_resource_class(self, form):
        """Test choose_export_resource_class() method"""
        admin = self.BaseModelExportChooseTest()
        self.assertEqual(
            admin.choose_export_resource_class(form, self.request), resources.Resource
        )

        form.data = {"django-import-export-resource": 1}
        self._prepend_form_prefix(form.data)
        self.assertEqual(
            admin.choose_export_resource_class(form, self.request), FooResource
        )

    class BaseModelImportChooseTest(mixins.BaseImportMixin):
        resource_classes = [resources.Resource, FooResource]

    @mock.patch("import_export.admin.ImportForm")
    def test_choose_import_resource_class(self, form):
        """Test choose_import_resource_class() method"""
        admin = self.BaseModelImportChooseTest()
        request = MagicMock(spec=HttpRequest)
        self.assertEqual(
            admin.choose_import_resource_class(form, request),
            resources.Resource,
        )

        form.data = {"django-import-export-resource": 1}
        self._prepend_form_prefix(form.data)
        self.assertEqual(admin.choose_import_resource_class(form, request), FooResource)


class BaseExportMixinTest(TestCase):
    class TestBaseExportMixin(mixins.BaseExportMixin):
        def get_export_resource_kwargs(self, request, **kwargs):
            self.kwargs = kwargs
            return super().get_resource_kwargs(request, **kwargs)

    def test_get_data_for_export_sets_kwargs(self):
        """
        issue 1268
        Ensure that get_export_resource_kwargs() handles the args and kwargs arguments.
        """
        request = MagicMock(spec=HttpRequest)
        m = self.TestBaseExportMixin()
        m.model = Book
        target_kwargs = {"a": 1}
        m.get_data_for_export(request, Book.objects.none(), **target_kwargs)
        self.assertEqual(m.kwargs, target_kwargs)

    def test_get_export_formats(self):
        class Format:
            def __init__(self, can_export):
                self.val = can_export

            def can_export(self):
                return self.val

        class CanExportFormat(Format):
            def __init__(self):
                super().__init__(True)

        class CannotExportFormat(Format):
            def __init__(self):
                super().__init__(False)

        class TestBaseExportMixin(mixins.BaseExportMixin):
            @property
            def export_formats(self):
                return [CanExportFormat, CannotExportFormat]

        m = TestBaseExportMixin()

        formats = m.get_export_formats()
        self.assertEqual(1, len(formats))
        self.assertEqual("CanExportFormat", formats[0].__name__)


class ExportMixinTest(TestCase):
    class TestExportMixin(admin.ExportMixin):
        def __init__(self, export_form) -> None:
            super().__init__()
            self.export_form = export_form

        def get_export_form(self):
            return self.export_form

    class TestExportForm(forms.ExportForm):
        pass

    def test_get_export_form(self):
        m = admin.ExportMixin()
        self.assertEqual(admin.ExportMixin.export_form_class, m.get_export_form_class())

    def test_get_export_form_with_custom_form(self):
        m = self.TestExportMixin(self.TestExportForm)
        self.assertEqual(self.TestExportForm, m.get_export_form())


class BaseExportImportMixinTest(TestCase):
    class TestMixin(mixins.BaseImportExportMixin):
        pass

    def test_get_resource_kwargs(self):
        mixin_instance = self.TestMixin()
        test_kwargs = {"key1": "value1", "key2": "value2"}
        mock_request = MagicMock(spec=HttpRequest)
        result = mixin_instance.get_resource_kwargs(mock_request, **test_kwargs)

        self.assertEqual(result, test_kwargs)
