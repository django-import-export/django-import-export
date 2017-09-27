import os
import pickle

from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail
from django.core.files.base import ContentFile
from django.test.testcases import TestCase

from import_export import resources, fields
from import_export.formats import base_formats
from import_export.tasks import (
    export_data, _get_email_message, _get_resource,
    _get_exported_data_as_attachment
)

from ..models import Book


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

    def test_task_sends_email(self):
        export_data(self.format.__class__.__name__, pickle.dumps(Book.objects.all().query), 'core.tests.export_task_tests.BookResource', {}, self.user.id, 'Test subject')
        self.assertEqual(1, len(mail.outbox))

    def test_file_created_at_right_location(self):
        user = User(email='test@example.com')
        file_name = 'test.txt'
        _get_email_message('test', user, ContentFile('text', name=file_name))
        file_path = os.path.join(settings.IMPORT_EXPORT_STORAGE_PATH, file_name)
        self.assertTrue(os.path.exists(file_path))
        os.remove(file_path)

    def test_get_resource_correctly_loads_resource_class(self):
        resource = _get_resource('core.tests.export_task_tests.BookResource', {})
        self.assertIsInstance(resource, BookResource)

    def test_get_eported_data_as_attachement_puts_queryset_data_into_file(self):
        books_export = _get_exported_data_as_attachment(self.format, BookResource(), pickle.dumps(Book.objects.all().query))
        self.assertIsInstance(books_export, ContentFile)

        book_list = Book.objects.all()
        expected_headers = 'published_date,id,name,author,author_email,published_time,price,categories'
        expected_rows = [expected_headers]

        for book in book_list:
            row = ',%s,%s,,,,,' % (book.id, book.name)
            expected_rows.append(row)
        expected_content = '\r\n'.join(expected_rows)
        expected_content += '\r\n'

        self.assertEqual(expected_content, books_export.read())
