from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.conf import settings
try:
    from django.urls import reverse
except ImportError:  # Django<2.0
    from django.core.urlresolvers import reverse
from django.test.client import RequestFactory
from django.test.testcases import TestCase

from import_export import admin as export_admin
from import_export.admin import load_class_from_settings
from import_export.exceptions import AsyncExportError
from import_export.formats.base_formats import CSV

from ..admin import BookAdmin
from ..models import Book

User = get_user_model()


class MockAsyncBackend(object):

    def create_task(self, format_name, query, resource_class_input_name, resource_kwargs, user_id, email_subject_line):
        pass


class MockAdminSite(object):
    name = 'Hello'


class AsyncExportTest(TestCase):

    def test_load_class_from_settings_loads_async_backend(self):
        AsyncBackend = load_class_from_settings('core.tests.test_async_export.MockAsyncBackend', 'Test')
        self.assertIsInstance(AsyncBackend(), MockAsyncBackend)

    def test_async_export_redirects_to_change_list_when_done(self):
        # Override module constants
        export_admin.ALLOW_ASYNC_EXPORT = True
        export_admin.ASYNC_EXPORT_BACKEND = MockAsyncBackend

        request = RequestFactory().get('')

        # Mock effects of messages middleware
        request.session = 'session'
        messages = FallbackStorage(request)
        setattr(request, '_messages', messages)

        user = User.objects.create(username='test_user')
        request.user = user

        Book.objects.create(name="Some book")
        book_admin = BookAdmin(Book, MockAdminSite())

        response = book_admin.handle_export(CSV, Book.objects.all(), request=request)
        expected_url = reverse('admin:%s_%s_changelist' % book_admin.get_model_info(),
                      current_app=MockAdminSite().name)

        # Reset module constants
        export_admin.ALLOW_ASYNC_EXPORT = False
        export_admin.ASYNC_EXPORT_BACKEND = None

        self.assertEqual(expected_url, response['Location'])

    def test_async_export_doesnt_run_when_no_backend_set(self):
        # Override module constants
        export_admin.ALLOW_ASYNC_EXPORT = True

        request = RequestFactory().get('')

        user = User.objects.create(username='test_user')
        request.user = user

        Book.objects.create(name="Some book")
        book_admin = BookAdmin(Book, MockAdminSite())

        response = book_admin.handle_export(CSV, Book.objects.all(), request=request)

        # Reset module constants
        export_admin.ALLOW_ASYNC_EXPORT = False

        # When exporting asynchronously, the response returned is a redirect
        self.assertEqual(200, response.status_code)

    def test_async_export_doesnt_run_when_allow_async_export_set_to_false(self):
        # Override module constants
        export_admin.ASYNC_EXPORT_BACKEND = MockAsyncBackend

        request = RequestFactory().get('')

        user = User.objects.create(username='test_user')
        request.user = user

        Book.objects.create(name="Some book")
        book_admin = BookAdmin(Book, MockAdminSite())

        response = book_admin.handle_export(CSV, Book.objects.all(), request=request)

        # Reset module constants
        export_admin.ASYNC_EXPORT_BACKEND = None

        # When exporting asynchronously, the response returned is a redirect
        self.assertEqual(200, response.status_code)

    def test_async_export_doesnt_run_when_too_few_items(self):
        # Override module constants
        export_admin.ALLOW_ASYNC_EXPORT = True
        export_admin.ASYNC_EXPORT_BACKEND = MockAsyncBackend
        export_admin.ASYNC_EXPORT_LEVEL = 2

        request = RequestFactory().get('')

        user = User.objects.create(username='test_user')
        request.user = user

        Book.objects.create(name="Some book")
        book_admin = BookAdmin(Book, MockAdminSite())

        response = book_admin.handle_export(CSV, Book.objects.all(), request=request)

        # Reset module constants
        export_admin.ALLOW_ASYNC_EXPORT = False
        export_admin.ASYNC_EXPORT_BACKEND = None
        export_admin.ASYNC_EXPORT_LEVEL = 0

        # When exporting asynchronously, the response returned is a redirect
        self.assertEqual(200, response.status_code)

    def test_exception_thrown_when_async_export_path_not_specified(self):
        # Override module constants
        export_admin.ALLOW_ASYNC_EXPORT = True
        export_admin.ASYNC_EXPORT_BACKEND = MockAsyncBackend
        export_admin.ASYNC_EXPORT_LEVEL = -1
        export_admin.ASYNC_EXPORT_STORAGE_PATH = "";

        request = RequestFactory().get('')

        user = User.objects.create(username='test_user')
        request.user = user

        Book.objects.create(name="Some book")
        book_admin = BookAdmin(Book, MockAdminSite())
        self.assertRaises(AsyncExportError, book_admin.handle_export, CSV, Book.objects.all(), request=request)

        # Reset module constants
        export_admin.ALLOW_ASYNC_EXPORT = False
        export_admin.ASYNC_EXPORT_BACKEND = None
        export_admin.ASYNC_EXPORT_LEVEL = 0
        export_admin.ASYNC_EXPORT_STORAGE_PATH = settings.IMPORT_EXPORT_STORAGE_PATH
