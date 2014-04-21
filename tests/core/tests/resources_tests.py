from __future__ import unicode_literals

from decimal import Decimal
from datetime import date
from copy import deepcopy

from django.test import (
        TestCase,
        TransactionTestCase,
        skipUnlessDBFeature,
        )
from django.utils.datastructures import SortedDict
from django.utils.html import strip_tags
from django.contrib.auth.models import User

import tablib

from import_export import resources
from import_export import fields
from import_export import widgets
from import_export import results
from import_export.instance_loaders import ModelInstanceLoader

from core.models import Book, Author, Category, Entry, Profile, Reader

try:
    from django.utils.encoding import force_text
except ImportError:
    from django.utils.encoding import force_unicode as force_text


class MyResource(resources.Resource):
    name = fields.Field()
    email = fields.Field()

    class Meta:
        export_order = ('email', 'name')


class ResourceTestCase(TestCase):

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
        msg = "invalid literal for int() with base 10: 'foo'"
        actual = result.rows[0].errors[0].error
        self.assertIsInstance(actual, ValueError)
        self.assertEqual("invalid literal for int() with base 10: 'foo'",
            str(actual))

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
            full_title = fields.Field(column_name="Full title")

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

    def test_widget_fomat_in_fk_field(self):
        class B(resources.ModelResource):

            class Meta:
                model = Book
                fields = ('author__birthday',)
                widgets = {
                    'author__birthday': {'format': '%Y-%m-%d'},
                }

        author = Author.objects.create(name="Author")
        self.book.author = author
        resource = B()
        result = resource.fields['author__birthday'].export(self.book)
        self.assertEqual(result, str(date.today()))

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

    def test_related_one_to_one(self):
        # issue #17 - Exception when attempting access something on the
        # related_name

        user = User.objects.create(username='foo')
        profile = Profile.objects.create(user=user)
        Entry.objects.create(user=user)
        Entry.objects.create(user=User.objects.create(username='bar'))

        class EntryResource(resources.ModelResource):
            class Meta:
                model = Entry
                fields = ('user__profile',)

        resource = EntryResource()
        dataset = resource.export(Entry.objects.all())
        self.assertEqual(dataset.dict[0]['user__profile'], profile.pk)
        self.assertEqual(dataset.dict[1]['user__profile'], '')

    def test_empty_get_queryset(self):
        # issue #25 - Overriding queryset on export() fails when passed
        # queryset has zero elements
        dataset = self.resource.export(Book.objects.none())
        self.assertEqual(len(dataset), 0)

    def test_import_data_skip_unchanged(self):
        def attempted_save(instance, real_dry_run):
            self.fail('Resource attempted to save instead of skipping')

        # Make sure we test with ManyToMany related objects
        cat1 = Category.objects.create(name='Cat 1')
        cat2 = Category.objects.create(name='Cat 2')
        self.book.categories.add(cat1)
        self.book.categories.add(cat2)
        dataset = self.resource.export()

        # Create a new resource that attempts to reimport the data currently
        # in the database while skipping unchanged rows (i.e. all of them)
        resource = deepcopy(self.resource)
        resource._meta.skip_unchanged = True
        # Fail the test if the resource attempts to save the row
        resource.save_instance = attempted_save
        result = resource.import_data(dataset, raise_errors=True)
        self.assertFalse(result.has_errors())
        self.assertEqual(len(result.rows), len(dataset))
        self.assertTrue(result.rows[0].diff)
        self.assertEqual(result.rows[0].import_type,
                results.RowResult.IMPORT_TYPE_SKIP)

        # Test that we can suppress reporting of skipped rows
        resource._meta.report_skipped = False
        result = resource.import_data(dataset, raise_errors=True)
        self.assertFalse(result.has_errors())
        self.assertEqual(len(result.rows), 0)

class ModelResourceTransactionTest(TransactionTestCase):

    def setUp(self):
        self.resource = BookResource()

    @skipUnlessDBFeature('supports_transactions')
    def test_m2m_import_with_transactions(self):
        cat1 = Category.objects.create(name='Cat 1')
        headers = ['id', 'name', 'categories']
        row = [None, 'FooBook', "%s" % cat1.pk]
        dataset = tablib.Dataset(row, headers=headers)

        result = self.resource.import_data(dataset, dry_run=True,
                use_transactions=True)

        row_diff = result.rows[0].diff
        fields = self.resource.get_fields()

        id_field = self.resource.fields['id']
        id_diff = row_diff[fields.index(id_field)]
        #id diff should exists because in rollbacked transaction
        #FooBook has been saved
        self.assertTrue(id_diff)

        category_field = self.resource.fields['categories']
        categories_diff = row_diff[fields.index(category_field)]
        self.assertEqual(strip_tags(categories_diff), force_text(cat1.pk))

        #check that it is really rollbacked
        self.assertFalse(Book.objects.filter(name='FooBook'))


class ModelResourceFactoryTest(TestCase):

    def test_create(self):
        BookResource = resources.modelresource_factory(Book)
        self.assertIn('id', BookResource.fields)
        self.assertEqual(BookResource._meta.model, Book)


class TranslationField(fields.Field):
    def get_value(self, obj):
        """
        Returns value for this field from object attribute.
        """
        return getattr(obj, 'title_%s' % self.attribute)

    def save(self, obj, data):
        if not self.readonly:
            setattr(obj, 'title_%s' % self.attribute, self.clean(data))


class MyDynamicResource(resources.Resource):
    id = fields.Field(attribute='id')
    author = fields.Field(attribute='author_email')

    class Meta:
        export_order = ('author', 'id')
        # We only need instance_loader_class because we're using Resource
        # instead of ModelResource, and we're only doing that to prove that
        # it works just as well with Resource as with ModelResource.
        instance_loader_class = ModelInstanceLoader
        # We only need to define model because ModelInstanceLoader needs it.
        model = Book

    def __init__(self, *args, **kwargs):
        # We only need to override __init__ to create a list of saved
        # instances, because we have no intention of writing them to the
        # database.
        super(MyDynamicResource, self).__init__(*args, **kwargs)
        self.saved_instances = []
        
    def get_dynamic_fields(self):
        # This is all you really need to do in the resource to support
        # dynamic fields.
        extra_fields = SortedDict()
        extra_fields['title_en'] = TranslationField(attribute='en',
            column_name="Title (English)")
        extra_fields['title_fr'] = TranslationField(attribute='fr',
            column_name="Title (French)")
        return extra_fields

    def get_import_id_fields(self):
        # We only need to implement this because ModelInstanceLoader needs it,
        # and we're not based on ModelResource that would provide it.
        return ['id']

    def init_instance(self, row=None):
        # We only need to implement this because we're not based on
        # ModelResource that would provide it.
        book = Book()
        book.title_en = None
        book.title_fr = None
        return book

    def save_instance(self, instance, dry_run=False):
        # We only need to implement this because we're not saving instances
        # to the database, because it has nowhere to store our extra fields
        # which are purely for demonstration purposes. Normally you would be
        # saving them in a different table, and the default 
        # fake saving of non-object instances for test purposes
        self.before_save_instance(instance, dry_run)
        if not dry_run:
            self.saved_instances.append(instance)
        self.after_save_instance(instance, dry_run)


class DynamicResourceTest(TestCase):

    def setUp(self):
        self.resource = MyDynamicResource()
        self.headers = self.resource.get_export_headers()
        self.dataset = tablib.Dataset(headers=self.headers)
        row = ['Albert Camus', '4', "The Stranger", "L'Etranger"]
        self.dataset.append(row)

    def test_fields(self):
        fields = self.resource.fields
        self.assertEqual(['author', 'id', 'title_en', 'title_fr'],
            sorted(fields.keys()))

    def test_field_column_names(self):
        # Also tests that the export order for fixed columns is respected.
        self.assertEqual(['author', 'id', 'Title (English)', 'Title (French)'],
            self.headers)

    def test_export(self):
        class FakeQueryset(list):
            def iterator(self):
                return self
        book = Book(id=5, author_email="Albert Camus")
        book.title_en = "The Stranger"
        book.title_fr = "L'Etranger"
        queryset = FakeQueryset([book])
        dataset = self.resource.export(queryset)
        self.assertEqual(len(dataset), 1)
        self.assertEqual(('Albert Camus', '5', "The Stranger", "L'Etranger"),
            dataset[0])

    def test_import(self):
        result = self.resource.import_data(self.dataset, raise_errors=True)

        self.assertFalse(result.has_errors())
        self.assertEqual(len(result.rows), 1)
        self.assertTrue(result.rows[0].diff)
        self.assertEqual(result.rows[0].import_type,
                results.RowResult.IMPORT_TYPE_NEW)

        self.assertEqual(len(self.resource.saved_instances), 1)
        instance = self.resource.saved_instances[0]
        self.assertEqual(instance.id, '4')
        self.assertEqual(instance.author_email, 'Albert Camus')
        self.assertEqual(instance.title_en, "The Stranger")
        self.assertEqual(instance.title_fr, "L'Etranger")


class DateReadField(fields.Field):
    def get_value(self, obj):
        """
        Returns value for this field from object attribute. Finds the
        appropriate value from the related set, using the field's attribute
        as the key (matching against User.username)
        """
        reader = obj.readers_cache.get(self.attribute, None)
        if reader:
            return reader.when
        else:
            return None

    def save(self, obj, data):
        if not self.readonly:
            try:
                d = data[self.column_name]
            except KeyError:
                raise KeyError("No column to extract %s value from "
                    "in %s" % (self.column_name, data))

            reader = obj.readers_cache.get(self.attribute, None)

            if reader:
                reader.when = d
            else:
                # no match, so create a new one
                user=User.objects.get(username=self.attribute)
                reader = Reader(user=user, book=obj, when=d)
                obj.readers_cache[self.attribute] = reader

            if reader is not None:
                obj.readers_dirty.append(reader)


class ExampleDynamicModelResource(resources.ModelResource):
    class Meta:
        fields = ('id', 'name')
        model = Book

    def get_dynamic_fields(self):
        # This is all you really need to do in the resource to support
        # dynamic fields.
        extra_fields = SortedDict()
        for user in User.objects.all():
            extra_fields[user.username] = DateReadField(attribute=user.username,
                column_name=user.last_name)
        return extra_fields

    def get_or_init_instance(self, instance_loader, row):
        # But we may need to hold associated Reader instances somewhere on
        # the object, until we're ready to save the object.

        instance, new = super(ExampleDynamicModelResource,
            self).get_or_init_instance(instance_loader, row)
        instance.readers_cache = {}
        instance.readers_dirty = []
        for reader in instance.reader_set.all():
            instance.readers_cache[reader.user.username] = reader
        return instance, new

    def export_resource(self, obj):
        if not hasattr(obj, 'readers_cache'):
            obj.readers_cache = {}
            for reader in obj.reader_set.all():
                obj.readers_cache[reader.user.username] = reader

        return [self.export_field(field, obj) for field in self.get_fields()]

    def save_instance(self, instance, dry_run=False):
        # And having cached the Reader objects, we need to write them to
        # the database, after the instance has been saved, and we've
        # updated the foreign key column.

        super(ExampleDynamicModelResource, self).save_instance(instance,
            dry_run)

        if not dry_run:
            for reader in instance.readers_dirty:
                from django.core.exceptions import ValidationError
                try:
                    reader.full_clean()
                    reader.save()
                except ValidationError as e:
                    # Model validation is optional, but catching the exception
                    # allows us to change the message to indicate which column
                    # caused it.
                    raise ValidationError("Reader %s: %s" %
                        (reader.user.username, e))


class ExampleDynamicModelResourceTest(TestCase):

    def setUp(self):
        self.narnia = Book.objects.create(name="Chronicles of Narnia")
        self.warand = Book.objects.create(name="War and Peace")
        self.cslewis = User.objects.create(username="lewis", last_name="Lewis")
        self.tolstoy = User.objects.create(username="tolstoy", last_name="Tolstoy")
        Reader.objects.create(user=self.cslewis, book=self.warand,
            when=date(1923,4,5))
        Reader.objects.create(user=self.tolstoy, book=self.narnia,
            when=date(1912,3,4))
        self.resource = ExampleDynamicModelResource()

    def test_fields(self):
        fields = self.resource.fields
        self.assertEqual(['id', 'lewis', 'name', 'tolstoy'],
            sorted(fields.keys()))

    def test_field_column_names(self):
        # Also tests that the export order for fixed columns is respected.
        headers = self.resource.get_export_headers()
        self.assertEqual(['id', 'name', 'Lewis', 'Tolstoy'], headers)

    def test_export(self):
        dataset = self.resource.export()
        self.assertEqual(len(dataset), 2)
        self.assertEqual((str(self.narnia.id), self.narnia.name, '', '1912-03-04'),
            dataset[0])
        self.assertEqual((str(self.warand.id), self.warand.name, '1923-04-05', ''),
            dataset[1])

    def test_import(self):
        self.headers = self.resource.get_export_headers()
        self.dataset = tablib.Dataset(headers=self.headers)
        row = [self.narnia.id, self.narnia.name, '1936-04-01', '1912-03-07']
        self.dataset.append(row)
        result = self.resource.import_data(self.dataset, raise_errors=True)

        self.assertFalse(result.has_errors())
        self.assertEqual(len(result.rows), 1)
        self.assertTrue(result.rows[0].diff)
        self.assertEqual(result.rows[0].import_type,
                results.RowResult.IMPORT_TYPE_UPDATE)

        readers = Reader.objects.all()
        self.assertEqual(sorted(str(r) for r in [
            Reader(user=self.cslewis, book=self.warand, when=date(1923,4,5)),
            Reader(user=self.tolstoy, book=self.narnia, when=date(1912,3,7)),
            Reader(user=self.cslewis, book=self.narnia, when=date(1936,4,1)),
            ]), sorted(str(r) for r in readers))
