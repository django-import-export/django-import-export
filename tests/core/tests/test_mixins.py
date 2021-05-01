from unittest import mock
from unittest.mock import MagicMock

from core.models import Book, Category
from django.http import HttpRequest
from django.test.testcases import TestCase
from django.urls import reverse

from import_export import formats, forms, mixins


class ExportViewMixinTest(TestCase):
    class TestExportForm(forms.ExportForm):
        cleaned_data = dict()

    def setUp(self):
        self.url = reverse('export-category')
        self.cat1 = Category.objects.create(name='Cat 1')
        self.cat2 = Category.objects.create(name='Cat 2')
        self.form = ExportViewMixinTest.TestExportForm(formats.base_formats.DEFAULT_FORMATS)
        self.form.cleaned_data["file_format"] = "0"

    def test_get(self):
        response = self.client.get(self.url)
        self.assertContains(response, self.cat1.name, status_code=200)
        self.assertEqual(response['Content-Type'], 'text/html; charset=utf-8')

    def test_post(self):
        data = {
            'file_format': '0',
        }
        response = self.client.post(self.url, data)
        self.assertContains(response, self.cat1.name, status_code=200)
        self.assertTrue(response.has_header("Content-Disposition"))
        self.assertEqual(response['Content-Type'], 'text/csv')

    def test_get_response_raises_TypeError_when_content_type_kwarg_used(self):
        """
        Test that HttpResponse is instantiated using the correct kwarg.
        """
        content_type = "text/csv"

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
            self.assertEqual(content_type, mock_http_response.call_args_list[0][1]["content_type"])
            self.assertEqual(content_type, mock_http_response.call_args_list[1][1]["mimetype"])

    def test_implements_get_filterset(self):
        """
        test that if the class-under-test defines a get_filterset()
        method, then this is called as required.
        """
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
        class Format(object):
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

        m = mixins.BaseImportMixin()
        m.formats = [CanImportFormat, CannotImportFormat]

        formats = m.get_import_formats()
        self.assertEqual(1, len(formats))
        self.assertEqual('CanImportFormat', formats[0].__name__)


class BaseExportMixinTest(TestCase):
    class TestBaseExportMixin(mixins.BaseExportMixin):
        def get_export_resource_kwargs(self, request, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs
            return super().get_resource_kwargs(request, *args, **kwargs)

    def test_get_data_for_export_sets_args_and_kwargs(self):
        """
        issue 1268
        Ensure that get_export_resource_kwargs() handles the args and kwargs arguments.
        """
        request = MagicMock(spec=HttpRequest)
        m = self.TestBaseExportMixin()
        m.model = Book
        target_args = (1,)
        target_kwargs = {"a": 1}
        m.get_data_for_export(request, Book.objects.none(), *target_args, **target_kwargs)
        self.assertEqual(m.args, target_args)
        self.assertEqual(m.kwargs, target_kwargs)

    def test_get_export_formats(self):
        class Format(object):
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

        m = mixins.BaseExportMixin()
        m.formats = [CanExportFormat, CannotExportFormat]

        formats = m.get_export_formats()
        self.assertEqual(1, len(formats))
        self.assertEqual('CanExportFormat', formats[0].__name__)
