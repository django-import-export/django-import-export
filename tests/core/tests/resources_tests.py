from django.test import TestCase

import tablib

from import_export import resources
from import_export import fields
from import_export import results
from import_export.instance_loaders import ModelInstanceLoader

from ..models import Book, Author


class MyResource(resources.Resource):
    name = fields.Field()
    email = fields.Field()

    class Meta:
        export_order = ('email', 'name')


class ResourceTest(TestCase):

    def setUp(self):
        self.my_resource = MyResource()

    def test_fields(self):
        fields = self.my_resource.fields
        self.assertIn('name', fields)

    def test_field_column_name(self):
        field = self.my_resource.fields['name']
        self.assertIn(field.column_name, 'name')

    def test_meta(self):
        self.assertIsInstance(self.my_resource._meta,
                resources.ResourceOptions)

    def test_get_export_order(self):
        self.assertEqual(self.my_resource.get_export_headers(),
                ['email', 'name'])


class BookResource(resources.ModelResource):
    published = fields.Field(column_name='published_date')

    class Meta:
        model = Book
        exclude = ('imported', )
        export_order = ('id', 'name', 'author_email', 'published')


class ModelResourceTest(TestCase):

    def setUp(self):
        self.resource = BookResource()

        self.book = Book.objects.create(name="Some book")
        self.dataset = tablib.Dataset(headers=['id', 'name', 'author_email'])
        row = [self.book.pk, 'Some book', 'test@example.com']
        self.dataset.append(row)

    def test_default_instance_loader_class(self):
        self.assertIs(self.resource._meta.instance_loader_class,
                ModelInstanceLoader)

    def test_fields(self):
        fields = self.resource.fields
        self.assertIn('id', fields)
        self.assertIn('name', fields)
        self.assertIn('author_email', fields)

    def test_excluded_fields(self):
        self.assertNotIn('imported', self.resource.fields)

    def test_init_instance(self):
        instance = self.resource.init_instance()
        self.assertIsInstance(instance, Book)

    def test_get_instance(self):
        instance_loader = self.resource._meta.instance_loader_class(
                self.resource)
        instance = self.resource.get_instance(instance_loader,
                self.dataset.dict[0])
        self.assertEqual(instance, self.book)

    def test_get_export_headers(self):
        headers = self.resource.get_export_headers()
        self.assertEqual(headers, ['id', 'name', 'author_email',
            'published_date'])

    def test_export(self):
        dataset = self.resource.export(Book.objects.all())
        self.assertEqual(len(dataset), 1)

    def test_get_diff(self):
        book2 = Book(name="Some other book")
        diff = self.resource.get_diff(self.book, book2)
        self.assertEqual(diff[1],
                u'<span>Some </span><ins style="background:#e6ffe6;">'
                u'other </ins><span>book</span>')
        self.assertFalse(diff[2])

    def test_import_data(self):
        result = self.resource.import_data(self.dataset, raise_errors=True)

        self.assertFalse(result.has_errors())
        self.assertEqual(len(result.rows), 1)
        self.assertTrue(result.rows[0].diff)
        self.assertEqual(result.rows[0].import_type,
                results.RowResult.IMPORT_TYPE_UPDATE)

        instance = Book.objects.get(pk=self.book.pk)
        self.assertEqual(instance.author_email, 'test@example.com')

    def test_import_data_error_saving_model(self):
        row = list(self.dataset.pop())
        # set pk to something that would yield error
        row[0] = 'foo'
        self.dataset.append(row)
        result = self.resource.import_data(self.dataset, raise_errors=False)

        self.assertTrue(result.has_errors())
        self.assertTrue(result.rows[0].errors)
        msg = 'ValueError("invalid literal for int() with base 10: \'foo\'",)'
        self.assertTrue(result.rows[0].errors[0].error, msg)

    def test_relationships_fields(self):

        class B(resources.ModelResource):
            class Meta:
                model = Book
                fields = ('author__name',)

        author = Author.objects.create(name="Author")
        self.book.author = author
        resource = B()
        result = resource.fields['author__name'].export(self.book)
        self.assertEqual(result, author.name)


class ModelResourceFactoryTest(TestCase):

    def test_create(self):
        BookResource = resources.modelresource_factory(Book)
        self.assertIn('id', BookResource.fields)
        self.assertEqual(BookResource._meta.model, Book)
