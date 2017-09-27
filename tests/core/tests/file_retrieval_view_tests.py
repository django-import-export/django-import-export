from django.test import TestCase
import uuid


class FileRetrievalViewTest(TestCase):
    def test_login_required(self):
        path = '/exported_files/%s.csv' % uuid.uuid4().hex
        response = self.client.get(path)
        self.assertEqual(302, response.status_code)
