import pickle

from django.contrib.auth.models import User
from django.core import mail
from django.test.testcases import TestCase

from import_export import resources, fields
from import_export.formats import base_formats
from import_export.tasks import export_data

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

    def test_task_sends_email_with_attachments(self):
        export_data(self.format.__class__.__name__, pickle.dumps(Book.objects.all().query), 'core.tests.export_task_tests.BookResource', {}, self.user.id, 'Test subject')
        self.assertEqual(1, len(mail.outbox))
