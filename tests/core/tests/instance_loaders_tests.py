from __future__ import unicode_literals

import tablib

from django.test import TestCase

from import_export import instance_loaders
from import_export import resources

from core.models import Book


class CachedInstanceLoaderTest(TestCase):

    def setUp(self):
        self.resource = resources.modelresource_factory(Book)()
        self.dataset = tablib.Dataset(headers=['id', 'name', 'author_email'])
        self.book = Book.objects.create(name="Some book")
        self.book2 = Book.objects.create(name="Some other book")
        row = [str(self.book.pk), 'Some book', 'test@example.com']
        self.dataset.append(row)
        self.instance_loader = instance_loaders.CachedInstanceLoader(
                self.resource, self.dataset)

    def test_all_instances(self):
        self.assertTrue(self.instance_loader.all_instances)
        self.assertEqual(len(self.instance_loader.all_instances), 1)
        self.assertEqual(list(self.instance_loader.all_instances.keys()),
                [self.book.pk])

    def test_get_instance(self):
        obj = self.instance_loader.get_instance(self.dataset.dict[0])
        self.assertEqual(obj, self.book)
