import tablib
from core.models import Book
from django.test import TestCase

from import_export import instance_loaders, resources


class BaseInstanceLoaderTest(TestCase):

    def test_get_instance(self):
        instance_loader = instance_loaders.BaseInstanceLoader(None)
        with self.assertRaises(NotImplementedError):
            instance_loader.get_instance(None)


class ModelInstanceLoaderTest(TestCase):

    def setUp(self):
        self.resource = resources.modelresource_factory(Book)()

    def test_get_instance_returns_None_when_params_is_empty(self):
        # setting an empty array of import_id_fields will mean
        # that 'params' is never set
        self.resource._meta.import_id_fields = []
        instance_loader = instance_loaders.ModelInstanceLoader(self.resource)
        self.assertIsNone(instance_loader.get_instance([]))


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
        self.assertEqual(list(self.instance_loader.all_instances),
                         [self.book.pk])

    def test_get_instance(self):
        obj = self.instance_loader.get_instance(self.dataset.dict[0])
        self.assertEqual(obj, self.book)


class CachedInstanceLoaderWithAbsentImportIdFieldTest(TestCase):
    """Ensure that the cache is empty when the PK field is absent
    in the inbound dataset.
    """

    def setUp(self):
        self.resource = resources.modelresource_factory(Book)()
        self.dataset = tablib.Dataset(headers=['name', 'author_email'])
        self.book = Book.objects.create(name="Some book")
        self.book2 = Book.objects.create(name="Some other book")
        row = ['Some book', 'test@example.com']
        self.dataset.append(row)
        self.instance_loader = instance_loaders.CachedInstanceLoader(
            self.resource, self.dataset)

    def test_all_instances(self):
        self.assertEqual(self.instance_loader.all_instances, {})
        self.assertEqual(len(self.instance_loader.all_instances), 0)

    def test_get_instance(self):
        obj = self.instance_loader.get_instance(self.dataset.dict[0])
        self.assertEqual(obj, None)
