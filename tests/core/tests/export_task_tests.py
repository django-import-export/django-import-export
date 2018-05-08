import io
import six
import os
import pickle

from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail
from django.test.testcases import TestCase

from import_export import resources, fields
from import_export.formats import base_formats
from import_export.tasks import export_data, ExportData

from ..models import Book


class Stack(list):

    def push(self, *args, **kwargs):
        return list.append(self, *args, **kwargs)


class BookResource(resources.ModelResource):
    published = fields.Field(column_name='published_date')

    class Meta:
        model = Book
        exclude = ('imported',)


class ExportTaskTests(TestCase):
    format = None

    def setUp(self):
        Book.objects.create(name='Book 1')
        Book.objects.create(name='Book 2')
        Book.objects.create(name='Book 3')

        self.format = base_formats.CSV()
        self.user = User(email='test@example.com')
        self.user.save()

        export_data_type = type(export_data)
        export_data_instance = ExportData()
        export_data_instance.request_stack = Stack()
        export_data_instance.file_format = self.format

        # This would normally be a function, but we don't have one so return
        # the object itself, which is callable
        export_data_instance.run = lambda: export_data_instance
        self.export_data_instance = export_data_type(export_data_instance)

    def test_task_sends_email(self):
        export_data(self.format.__class__.__name__, pickle.dumps(Book.objects.all().query), 'core.tests.export_task_tests.BookResource', {}, self.user.id, 'Test subject')
        self.assertEqual(1, len(mail.outbox))

    def test_task_gets_user_from_id(self):
        user = export_data.get_user(self.user.id)
        self.assertEqual(self.user.id, user.id)

    def test_get_filename_returns_32_bit_hex_dot_extension(self):
        self.export_data_instance.file_format = self.format
        file_name = self.export_data_instance.get_file_name()
        six.assertRegex(self, file_name, '[0-9a-f]{32}\.\w{3,4}')

    def test_file_created_at_right_location(self):
        self.export_data_instance.file_name = self.export_data_instance.get_file_name()
        self.export_data_instance.resource = BookResource()
        self.export_data_instance.queryset = Book.objects.all()
        self.export_data_instance.export_data(Book.objects.all())
        file_path = os.path.join(settings.IMPORT_EXPORT_STORAGE_PATH, self.export_data_instance.file_name)
        self.assertTrue(os.path.exists(file_path))
        os.remove(file_path)

    def test_get_resource_correctly_loads_resource_class(self):
        resource = export_data.get_resource('core.tests.export_task_tests.BookResource', {})
        self.assertIsInstance(resource, BookResource)

    def test_get_email_from_user(self):
        self.export_data_instance.user = self.user
        self.assertEqual(self.user.email, self.export_data_instance.get_email_address())

    def test_deserialize_query_returns_query_object(self):
        expected_query = Book.objects.all().query
        query = pickle.dumps(expected_query)
        actual_query = export_data.deserialize_query(query)
        self.assertEqual(str(expected_query), str(actual_query))

    def test_email_sent_when_a_task_fails(self):
        self.export_data_instance.resource = BookResource()
        self.export_data_instance.user = self.user
        self.export_data_instance.on_failure(None, 1, [], {}, None)

        self.assertEqual(1, len(mail.outbox))

    def test_email_only_sent_when_there_is_user(self):
        self.export_data_instance.user = None
        self.export_data_instance.on_failure(None, 1, [], {}, None)

        self.assertEqual(0, len(mail.outbox))

    def test_no_email_body_when_no_resource(self):
        self.export_data_instance.user = self.user
        self.export_data_instance.on_failure(None, 1, [], {}, None)
        email = mail.outbox[0]

        self.assertEqual('', email.body)

    def test_no_subject_is_export_failed_when_no_resource(self):
        self.export_data_instance.user = self.user
        self.export_data_instance.on_failure(None, 1, [], {}, None)
        email = mail.outbox[0]

        self.assertEqual('Export failed', email.subject)

    def test_export_data_puts_queryset_data_into_file(self):
        self.export_data_instance.file_format = self.format
        self.export_data_instance.resource = BookResource()
        self.export_data_instance.queryset = Book.objects.all()
        self.export_data_instance.file_name = self.export_data_instance.get_file_name()

        self.export_data_instance.export_data()

        file_path = os.path.join(settings.IMPORT_EXPORT_STORAGE_PATH, self.export_data_instance.file_name)
        book_list = Book.objects.all()
        expected_headers = 'published_date,id,name,author,author_email,published_time,price,categories'
        expected_rows = [expected_headers]

        for book in book_list:
            row = ',%s,%s,,,,,' % (book.id, book.name)
            expected_rows.append(row)
        expected_content = '\r\n'.join(expected_rows)
        expected_content += '\r\n'

        with io.open(file_path, 'r', newline='\r\n') as books_export:
            self.assertEqual(expected_content, books_export.read())
