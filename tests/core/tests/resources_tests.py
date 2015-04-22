from __future__ import unicode_literals

from decimal import Decimal
from datetime import date
from copy import deepcopy

from django.db import models
from django.db.models.fields import FieldDoesNotExist
from django.test import (
        TestCase,
        TransactionTestCase,
        skipUnlessDBFeature,
        )
from django.utils.html import strip_tags
from django.contrib.auth.models import User

import tablib

from import_export import resources
from import_export import fields
from import_export import widgets
from import_export import results
from import_export.instance_loaders import ModelInstanceLoader

from core.models import Book, Author, Category, Entry, Profile

try:
    from django.utils.encoding import force_text
except ImportError:
    from django.utils.encoding import force_unicode as force_text


class MyResource(resources.Resource):
    name = fields.Field()
    email = fields.Field()
    extra = fields.Field()

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
                ['email', 'name', 'extra'])

    # Issue 140 Attributes aren't inherited by subclasses
    def test_inheritance(self):
        class A(MyResource):
            inherited = fields.Field()

            class Meta:
                import_id_fields = ('email',)

        class B(A):
            local = fields.Field()

            class Meta:
                export_order = ('email', 'extra')

        resource = B()
        self.assertIn('name', resource.fields)
        self.assertIn('inherited', resource.fields)
        self.assertIn('local', resource.fields)
        self.assertEqual(resource.get_export_headers(),
                ['email', 'extra', 'name', 'inherited', 'local'])
        self.assertEqual(resource._meta.import_id_fields, ('email',))

    def test_inheritance_with_custom_attributes(self):
        class A(MyResource):
            inherited = fields.Field()

            class Meta:
                import_id_fields = ('email',)
                custom_attribute = True

        class B(A):
            local = fields.Field()

        resource = B()
        self.assertEqual(resource._meta.custom_attribute, True)

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

    def test_get_instance_with_missing_field_data(self):
        instance_loader = self.resource._meta.instance_loader_class(
                self.resource)
        # construct a dataset with a missing "id" column
        dataset = tablib.Dataset(headers=['name', 'author_email', 'price'])
        dataset.append(['Some book', 'test@example.com', "10.25"])
        with self.assertRaises(KeyError) as cm:
            instance = self.resource.get_instance(instance_loader,
                dataset.dict[0])
        self.assertEqual(u"Column 'id' not found in dataset. Available columns "
            "are: %s" % [u'name', u'author_email', u'price'], cm.exception.args[0])

    def test_get_export_headers(self):
        headers = self.resource.get_export_headers()
        self.assertEqual(headers, ['published_date',
            'id', 'name', 'author', 'author_email', 'price', 'categories',
            ])

    def test_export(self):
        dataset = self.resource.export(Book.objects.all())
        self.assertEqual(len(dataset), 1)

    def test_export_iterable(self):
        dataset = self.resource.export(list(Book.objects.all()))
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

    def test_import_data_value_error_includes_field_name(self):
        class AuthorResource(resources.ModelResource):
            class Meta:
                model = Author

        resource = AuthorResource()
        dataset = tablib.Dataset(headers=['id', 'name', 'birthday'])
        dataset.append(['', 'A.A.Milne', '1882test-01-18'])

        result = resource.import_data(dataset, raise_errors=False)

        self.assertTrue(result.has_errors())
        self.assertTrue(result.rows[0].errors)
        msg = ("Column 'birthday': Enter a valid date/time.")
        actual = result.rows[0].errors[0].error
        self.assertIsInstance(actual, ValueError)
        self.assertEqual(msg, str(actual))

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
        self.assertEqual("Column 'id': invalid literal for int() with "
            "base 10: 'foo'", str(actual))

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

    def test_m2m_options_import(self):
        cat1 = Category.objects.create(name='Cat 1')
        cat2 = Category.objects.create(name='Cat 2')
        headers = ['id', 'name', 'categories']
        row = [None, 'FooBook', "Cat 1|Cat 2"]
        dataset = tablib.Dataset(row, headers=headers)

        class BookM2MResource(resources.ModelResource):
            categories = fields.Field(
                attribute='categories',
                widget=widgets.ManyToManyWidget(Category, field='name',
                                                separator='|')
            )

            class Meta:
                model = Book

        resource = BookM2MResource()
        resource.import_data(dataset, raise_errors=True)
        book = Book.objects.get(name='FooBook')
        self.assertIn(cat1, book.categories.all())
        self.assertIn(cat2, book.categories.all())

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
                fields = ('user__profile', 'user__profile__is_private')

        resource = EntryResource()
        dataset = resource.export(Entry.objects.all())
        self.assertEqual(dataset.dict[0]['user__profile'], profile.pk)
        self.assertEqual(dataset.dict[0]['user__profile__is_private'], '1')
        self.assertEqual(dataset.dict[1]['user__profile'], '')
        self.assertEqual(dataset.dict[1]['user__profile__is_private'], '')

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

    def test_before_import_access_to_kwargs(self):
        class B(BookResource):
            def before_import(self, dataset, dry_run, **kwargs):
                if 'extra_arg' in kwargs:
                    dataset.headers[dataset.headers.index('author_email')] = 'old_email'
                    dataset.insert_col(0,
                                       lambda row: kwargs['extra_arg'],
                                       header='author_email')

        resource = B()
        result = resource.import_data(self.dataset, raise_errors=True,
                                      extra_arg='extra@example.com')
        self.assertFalse(result.has_errors())
        self.assertEqual(len(result.rows), 1)
        instance = Book.objects.get(pk=self.book.pk)
        self.assertEqual(instance.author_email, 'extra@example.com')

    def test_link_to_nonexistent_field(self):
        with self.assertRaises(FieldDoesNotExist) as cm:
            class BrokenBook(resources.ModelResource):
                class Meta:
                    model = Book
                    fields = ('nonexistent__invalid',)
        self.assertEqual("Book.nonexistent: Book has no field named 'nonexistent'",
            cm.exception.args[0])

        with self.assertRaises(FieldDoesNotExist) as cm:
            class BrokenBook(resources.ModelResource):
                class Meta:
                    model = Book
                    fields = ('author__nonexistent',)
        self.assertEqual("Book.author.nonexistent: Author has no field named "
            "'nonexistent'", cm.exception.args[0])

    def test_link_to_nonrelation_field(self):
        with self.assertRaises(KeyError) as cm:
            class BrokenBook(resources.ModelResource):
                class Meta:
                    model = Book
                    fields = ('published__invalid',)
        self.assertEqual("Book.published is not a relation",
            cm.exception.args[0])

        with self.assertRaises(KeyError) as cm:
            class BrokenBook(resources.ModelResource):
                class Meta:
                    model = Book
                    fields = ('author__name__invalid',)
        self.assertEqual("Book.author.name is not a relation",
            cm.exception.args[0])

    def test_override_field_construction_in_resource(self):
        class B(resources.ModelResource):
            class Meta:
                model = Book
                fields = ('published',)

            @classmethod
            def field_from_django_field(self, field_name, django_field, readonly):
                if field_name == 'published':
                    return {'sound': 'quack'}

        resource = B()
        self.assertEqual({'sound': 'quack'}, B.fields['published'])


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
