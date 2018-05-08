import os
import uuid

from django.conf import settings
from django.contrib.auth.models import User
from django.http.response import Http404
from django.test import TestCase

from import_export.formats.base_formats import CSV, XLSX


class FileRetrievalViewTest(TestCase):

    def setUp(self):
        self.username = 'test_user'
        self.password = 'password'

        user = User.objects.create(username='test_user')
        user.set_password('password')
        user.save()

    def test_login_required(self):
        path = '/exported_files/%s.csv' % uuid.uuid4().hex
        response = self.client.get(path)
        self.assertEqual(302, response.status_code)

    def test_view_rejects_files_with_multiple_periods_in_name(self):

        self.client.login(username=self.username, password=self.password)

        path = '/exported_files/..%s.csv' % uuid.uuid4().hex
        response = self.client.get(path)
        self.assertEqual(404, response.status_code)

    def test_view_returns_response_for_valid_files(self):
        file_name = uuid.uuid4().hex + '.csv'
        full_file_name = os.path.join(settings.IMPORT_EXPORT_STORAGE_PATH, file_name)
        with open(full_file_name, 'w') as a_file:
            pass

        path = '/exported_files/%s' % file_name

        self.client.login(username=self.username, password=self.password)
        response = self.client.get(path)
        self.assertEqual(200, response.status_code)

    def test_view_returns_file_contents_when_valid(self):
        file_name = uuid.uuid4().hex + '.csv'
        full_file_name = os.path.join(settings.IMPORT_EXPORT_STORAGE_PATH, file_name)
        expected_content = 'This is a test.'
        with open(full_file_name, 'w') as a_file:
            a_file.write(expected_content)

        path = '/exported_files/%s' % file_name

        self.client.login(username=self.username, password=self.password)
        response = self.client.get(path)
        self.assertEqual(expected_content.encode(response.charset), response.content)

    def test_view_returns_file_content_type_for_csv_when_valid(self):
        file_name = uuid.uuid4().hex + '.csv'
        full_file_name = os.path.join(settings.IMPORT_EXPORT_STORAGE_PATH, file_name)

        with open(full_file_name, 'w') as a_file:
            pass

        path = '/exported_files/%s' % file_name

        csv_format = CSV()
        expected_content_type = csv_format.get_content_type()

        self.client.login(username=self.username, password=self.password)
        response = self.client.get(path)
        actual_content_type = response['Content-Type']

        self.assertEqual(expected_content_type, actual_content_type)

    def test_view_returns_file_content_type_for_xlsx_when_valid(self):
        file_name = uuid.uuid4().hex + '.xlsx'
        full_file_name = os.path.join(settings.IMPORT_EXPORT_STORAGE_PATH, file_name)

        with open(full_file_name, 'w') as a_file:
            a_file.write('This is a test.')

        path = '/exported_files/%s' % file_name

        xlsx_format = XLSX()
        expected_content_type = xlsx_format.get_content_type()

        self.client.login(username=self.username, password=self.password)
        response = self.client.get(path)
        actual_content_type = response['Content-Type']

        self.assertEqual(expected_content_type, actual_content_type)

    def test_view_returns_404_when_file_type_invalid(self):
        file_name = uuid.uuid4().hex + '.abc'
        full_file_name = os.path.join(settings.IMPORT_EXPORT_STORAGE_PATH, file_name)

        with open(full_file_name, 'w') as a_file:
            pass

        path = '/exported_files/%s' % file_name

        self.client.login(username=self.username, password=self.password)
        response = self.client.get(path)

        self.assertEqual(404, response.status_code)

    def test_content_disposition_set(self):
        file_name = uuid.uuid4().hex + '.csv'
        full_file_name = os.path.join(settings.IMPORT_EXPORT_STORAGE_PATH, file_name)

        with open(full_file_name, 'w') as a_file:
            pass

        path = '/exported_files/%s' % file_name

        self.client.login(username=self.username, password=self.password)

        response = self.client.get(path)

        expected_content_disposition = 'attachment; filename=%s' % file_name
        actual_content_disposition = response['Content-Disposition']

        self.assertEqual(expected_content_disposition, actual_content_disposition)
