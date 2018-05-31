from __future__ import unicode_literals
from django.test.testcases import TestCase
try:
    from django.urls import reverse
except ImportError:
    from django.core.urlresolvers import reverse
from core.models import Category


class ExportViewMixinTest(TestCase):

    def setUp(self):
        self.url = reverse('export-category')
        self.cat1 = Category.objects.create(name='Cat 1')
        self.cat2 = Category.objects.create(name='Cat 2')

    def test_get(self):
        response = self.client.get(self.url)
        self.assertContains(response, self.cat1.name, status_code=200)
        self.assertTrue(response['Content-Type'], 'text/html')

    def test_post(self):
        data = {
            'file_format': '0',
        }
        response = self.client.post(self.url, data)
        self.assertContains(response, self.cat1.name, status_code=200)
        self.assertTrue(response.has_header("Content-Disposition"))
        self.assertTrue(response['Content-Type'], 'text/csv')
