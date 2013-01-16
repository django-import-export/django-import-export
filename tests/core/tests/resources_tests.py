from decimal import Decimal
from datetime import date

from django.test import TestCase

import tablib

from import_export import resources
from import_export import fields
from import_export import widgets
from import_export import results
from import_export.instance_loaders import ModelInstanceLoader

from ..models import Book, Author, Category


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


class ModelResourceTest(TestCase):

    def setUp(self):
        self.resource = BookResource()

        self.book = Book.objects.create(name="Some book")
        self.dataset = tablib.Dataset(headers=['id', 'name', 'author_email',
            'price'])
        row = [self.book.pk, 'Some book', 'test@example.com', "10.25"]
        self.dataset.append(row)

    def test_default_instance_loader_class(self):
        self.assertIs(self.resource._meta.instance_loader_class,
                ModelInstanceLoader)

    def test_fields(self):
        fields = self.resource.fields
        self.assertIn('id', fields)
        self.assertIn('name', fields)
        self.assertIn('author_email', fields)
        self.assertIn('price', fields)

    def test_fields_foreign_key(self):
        fields = self.resource.fields
        self.assertIn('author', fields)
        widget = fields['author'].widget
        self.assertIsInstance(widget, widgets.ForeignKeyWidget)
        self.assertEqual(widget.model, Author)

    def test_fields_m2m(self):
        fields = self.resource.fields
        self.assertIn('categories', fields)

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
        self.assertEqual(headers, ['published_date',
            'id', 'name', 'author', 'author_email', 'price', 'categories',
            ])

    def test_export(self):
        dataset = self.resource.export(Book.objects.all())
        self.assertEqual(len(dataset), 1)

    def test_get_diff(self):
        book2 = Book(name="Some other book")
        diff = self.resource.get_diff(self.book, book2)
        headers = self.resource.get_export_headers()
        self.assertEqual(diff[headers.index('name')],
                u'<span>Some </span><ins style="background:#e6ffe6;">'
                u'other </ins><span>book</span>')
        self.assertFalse(diff[headers.index('author_email')])

    def test_import_data(self):
        result = self.resource.import_data(self.dataset, raise_errors=True)

        self.assertFalse(result.has_errors())
        self.assertEqual(len(result.rows), 1)
        self.assertTrue(result.rows[0].diff)
        self.assertEqual(result.rows[0].import_type,
                results.RowResult.IMPORT_TYPE_UPDATE)

        instance = Book.objects.get(pk=self.book.pk)
        self.assertEqual(instance.author_email, 'test@example.com')
        self.assertEqual(instance.price, Decimal("10.25"))

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

    def test_import_data_delete(self):

        class B(BookResource):
            delete = fields.Field(widget=widgets.BooleanWidget())

            def for_delete(self, row, instance):
                return self.fields['delete'].clean(row)

        row = [self.book.pk, self.book.name, '1']
        dataset = tablib.Dataset(*[row], headers=['id', 'name', 'delete'])
        result = B().import_data(dataset, raise_errors=True)
        self.assertFalse(result.has_errors())
        self.assertEqual(result.rows[0].import_type,
                results.RowResult.IMPORT_TYPE_DELETE)
        self.assertFalse(Book.objects.filter(pk=self.book.pk))

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

    def test_dehydrating_fields(self):

        class B(resources.ModelResource):
            full_title = fields.Field()

            class Meta:
                model = Book
                fields = ('author__name', 'full_title')

            def dehydrate_full_title(self, obj):
                return '%s by %s' % (obj.name, obj.author.name)

        author = Author.objects.create(name="Author")
        self.book.author = author
        resource = B()
        full_title = resource.export_field(resource.get_fields()[0], self.book)
        self.assertEqual(full_title, '%s by %s' % (self.book.name, self.book.author.name))

    def test_widget_kwargs_for_field(self):

        class B(resources.ModelResource):

            class Meta:
                model = Book
                fields = ('published',)
                widgets = {
                        'published': {'format': '%d.%m.%Y'},
                        }

        resource = B()
        self.book.published = date(2012, 8, 13)
        result = resource.fields['published'].export(self.book)
        self.assertEqual(result, "13.08.2012")

    def test_foreign_keys_export(self):
        author1 = Author.objects.create(name='Foo')
        self.book.author = author1
        self.book.save()

        dataset = self.resource.export(Book.objects.all())
        self.assertEqual(dataset.dict[0]['author'], author1.pk)

    def test_foreign_keys_import(self):
        author2 = Author.objects.create(name='Bar')
        headers = ['id', 'name', 'author']
        row = [None, 'FooBook', author2.pk]
        dataset = tablib.Dataset(row, headers=headers)
        self.resource.import_data(dataset, raise_errors=True)

        book = Book.objects.get(name='FooBook')
        self.assertEqual(book.author, author2)

    def test_m2m_export(self):
        cat1 = Category.objects.create(name='Cat 1')
        cat2 = Category.objects.create(name='Cat 2')
        self.book.categories.add(cat1)
        self.book.categories.add(cat2)

        dataset = self.resource.export(Book.objects.all())
        self.assertEqual(dataset.dict[0]['categories'],
                '%d,%d' % (cat1.pk, cat2.pk))

    def test_m2m_import(self):
        cat1 = Category.objects.create(name='Cat 1')
        headers = ['id', 'name', 'categories']
        row = [None, 'FooBook', "%s" % cat1.pk]
        dataset = tablib.Dataset(row, headers=headers)
        self.resource.import_data(dataset, raise_errors=True)

        book = Book.objects.get(name='FooBook')
        self.assertIn(cat1, book.categories.all())


class ModelResourceFactoryTest(TestCase):

    def test_create(self):
        BookResource = resources.modelresource_factory(Book)
        self.assertIn('id', BookResource.fields)
        self.assertEqual(BookResource._meta.model, Book)
