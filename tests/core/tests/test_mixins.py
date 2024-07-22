import warnings
from unittest import mock
from unittest.mock import MagicMock

from core.models import Book, Category
from django.http import HttpRequest
from django.test.testcases import TestCase
from django.urls import reverse

from import_export import admin, formats, forms, mixins, resources
from import_export.resources import modelresource_factory


class ExportViewMixinTest(TestCase):
    class TestExportForm(forms.ExportForm):
        cleaned_data = {}

    def setUp(self):
        self.url = reverse("export-category")
        self.cat1 = Category.objects.create(name="Cat 1")
        self.cat2 = Category.objects.create(name="Cat 2")
        self.resource = modelresource_factory(Category)
        self.form = ExportViewMixinTest.TestExportForm(
            formats=formats.base_formats.DEFAULT_FORMATS,
            resources=[self.resource],
        )
        self.form.cleaned_data["format"] = "0"

    def test_get(self):
        response = self.client.get(self.url)
        self.assertContains(response, self.cat1.name, status_code=200)
        self.assertEqual(response["Content-Type"], "text/html; charset=utf-8")

    def test_post(self):
        data = {"format": "0", "categoryresource_id": True}
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            response = self.client.post(self.url, data)
        self.assertContains(response, self.cat1.name, status_code=200)
        self.assertTrue(response.has_header("Content-Disposition"))
        self.assertEqual(response["Content-Type"], "text/csv")

    def test_get_response_raises_TypeError_when_content_type_kwarg_used(self):
        """
        Test that HttpResponse is instantiated using the correct kwarg.
        """
        content_type = "text/csv"

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=DeprecationWarning)

            class TestMixin(mixins.ExportViewFormMixin):
                def __init__(self):
                    self.model = MagicMock()
                    self.request = MagicMock(spec=HttpRequest)
                    self.model.__name__ = "mockModel"

                def get_queryset(self):
                    return MagicMock()

        m = TestMixin()
        with mock.patch("import_export.mixins.HttpResponse") as mock_http_response:
            # on first instantiation, raise TypeError, on second, return mock
            mock_http_response.side_effect = [TypeError(), mock_http_response]
            m.form_valid(self.form)
            self.assertEqual(
                content_type, mock_http_response.call_args_list[0][1]["content_type"]
            )
            self.assertEqual(
                content_type, mock_http_response.call_args_list[1][1]["mimetype"]
            )

    def test_implements_get_filterset(self):
        """
        test that if the class-under-test defines a get_filterset()
        method, then this is called as required.
        """

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=DeprecationWarning)

            class TestMixin(mixins.ExportViewFormMixin):
                mock_get_filterset_call_count = 0
                mock_get_filterset_class_call_count = 0

                def __init__(self):
                    self.model = MagicMock()
                    self.request = MagicMock(spec=HttpRequest)
                    self.model.__name__ = "mockModel"

                def get_filterset(self, filterset_class):
                    self.mock_get_filterset_call_count += 1
                    return MagicMock()

                def get_filterset_class(self):
                    self.mock_get_filterset_class_call_count += 1
                    return MagicMock()

        m = TestMixin()
        res = m.form_valid(self.form)
        self.assertEqual(200, res.status_code)
        self.assertEqual(1, m.mock_get_filterset_call_count)
        self.assertEqual(1, m.mock_get_filterset_class_call_count)


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


class MixinModelAdminTest(TestCase):
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

    class BaseModelResourceClassTest(mixins.BaseImportMixin, mixins.BaseExportMixin):
        resource_class = resources.Resource
        export_call_count = 0
        import_call_count = 0

        def get_export_resource_class(self):
            self.export_call_count += 1

        def get_import_resource_class(self):
            self.import_call_count += 1

    def test_deprecated_resource_class_raises_warning(self):
        """Test that the mixin throws error if user didn't
        migrate to resource_classes"""
        admin = self.BaseModelResourceClassTest()
        msg = (
            "The 'get_export_resource_class()' method has been deprecated. "
            "Please implement the new 'get_export_resource_classes()' method in "
            "core.tests.test_mixins.MixinModelAdminTest.BaseModelResourceClassTest"
        )
        with self.assertWarns(DeprecationWarning, msg=msg):
            admin.get_export_resource_classes(self.request)

        msg = (
            "The 'get_import_resource_class()' method has been deprecated. "
            "Please implement the new 'get_import_resource_classes()' method in "
            "core.tests.test_mixins.MixinModelAdminTest.BaseModelResourceClassTest"
        )
        with self.assertWarns(DeprecationWarning, msg=msg):
            admin.get_import_resource_classes(self.request)

        msg = (
            "The 'resource_class' field has been deprecated. "
            "Please implement the new 'resource_classes' field in "
            "core.tests.test_mixins.MixinModelAdminTest.BaseModelResourceClassTest"
        )
        with self.assertWarns(DeprecationWarning, msg=msg):
            self.assertEqual(
                admin.get_resource_classes(self.request), [resources.Resource]
            )

        self.assertEqual(1, admin.export_call_count)
        self.assertEqual(1, admin.import_call_count)

    class BaseModelGetExportResourceClassTest(mixins.BaseExportMixin):
        def get_resource_class(self):
            pass

    def test_deprecated_get_resource_class_raises_warning(self):
        """Test that the mixin throws error if user
        didn't migrate to resource_classes"""
        admin = self.BaseModelGetExportResourceClassTest()
        msg = (
            "The 'get_resource_class()' method has been deprecated. "
            "Please implement the new 'get_resource_classes()' method in "
            "core.tests.test_mixins.MixinModelAdminTest."
            "BaseModelGetExportResourceClassTest"
        )
        with self.assertWarns(DeprecationWarning, msg=msg):
            admin.get_resource_classes(self.request)

    class BaseModelAdminFaultyResourceClassesTest(mixins.BaseExportMixin):
        resource_classes = resources.Resource

    def test_faulty_resource_class_raises_exception(self):
        """Test fallback mechanism to old get_export_resource_class() method"""
        admin = self.BaseModelAdminFaultyResourceClassesTest()
        with self.assertRaisesRegex(
            Exception, r"^The resource_classes field type must be subscriptable"
        ):
            admin.get_export_resource_classes(self.request)

    class BaseModelAdminBothResourceTest(mixins.BaseExportMixin):
        call_count = 0

        resource_class = resources.Resource
        resource_classes = [resources.Resource]

    def test_both_resource_class_raises_exception(self):
        """Test fallback mechanism to old get_export_resource_class() method"""
        admin = self.BaseModelAdminBothResourceTest()
        with self.assertRaisesRegex(
            Exception, "Only one of 'resource_class' and 'resource_classes' can be set"
        ):
            admin.get_export_resource_classes(self.request)

    class BaseModelExportChooseTest(mixins.BaseExportMixin):
        resource_classes = [resources.Resource, FooResource]

    @mock.patch("import_export.admin.SelectableFieldsExportForm")
    def test_choose_export_resource_class(self, form):
        """Test choose_export_resource_class() method"""
        admin = self.BaseModelExportChooseTest()
        self.assertEqual(
            admin.choose_export_resource_class(form, self.request), resources.Resource
        )

        form.cleaned_data = {"resource": 1}
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

        form.cleaned_data = {"resource": 1}
        self.assertEqual(admin.choose_import_resource_class(form, request), FooResource)

    class BaseModelResourceClassOldTest(mixins.BaseImportMixin, mixins.BaseExportMixin):
        def get_resource_class(self):
            return FooResource

    def test_get_resource_class_old(self):
        """
        Test that if only the old get_resource_class() method is defined,
        the get_export_resource_classes() and get_import_resource_classes()
        still return list of resources.
        """
        admin = self.BaseModelResourceClassOldTest()
        msg = (
            "The 'get_resource_class()' method has been deprecated. "
            "Please implement the new 'get_resource_classes()' method in "
            "core.tests.test_mixins.MixinModelAdminTest.BaseModelResourceClassOldTest"
        )
        with self.assertWarns(DeprecationWarning, msg=msg):
            self.assertEqual(
                admin.get_export_resource_classes(self.request), [FooResource]
            )
        with self.assertWarns(DeprecationWarning, msg=msg):
            self.assertEqual(
                admin.get_import_resource_classes(self.request), [FooResource]
            )


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
