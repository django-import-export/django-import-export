# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import tablib
from collections import OrderedDict
from copy import deepcopy
from datetime import date
from decimal import Decimal
from unittest import skip, skipUnless

from django.conf import settings
from django.contrib.auth.models import User
from django.db import IntegrityError, DatabaseError
from django.db.models import Count
from django.db.models.fields import FieldDoesNotExist
from django.test import TestCase, TransactionTestCase, skipUnlessDBFeature
from django.utils import six
from django.utils.html import strip_tags
from django.utils.encoding import force_text

from import_export import fields, resources, results, widgets
from import_export.instance_loaders import ModelInstanceLoader
from import_export.resources import Diff

from ..models import (
    Author, Book, Category, Entry, Profile, WithDefault, WithDynamicDefault,
    WithFloatField, Person, Role
)


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
        """Check that fields were determined correctly """

        # check that our fields were determined
        self.assertIn('name', self.my_resource.fields)

        # check that resource instance fields attr isn't link to resource cls
        # fields
        self.assertFalse(
            MyResource.fields is self.my_resource.fields
        )

        # dynamically add new resource field into resource instance
        self.my_resource.fields.update(
            OrderedDict([
                ('new_field', fields.Field()),
            ])
        )

        # check that new field in resource instance fields
        self.assertIn(
            'new_field',
            self.my_resource.fields
        )

        # check that new field not in resource cls fields
        self.assertNotIn(
            'new_field',
            MyResource.fields
        )

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


class AuthorResource(resources.ModelResource):

    books = fields.Field(
        column_name='books',
        attribute='book_set',
        readonly=True,
    )

    class Meta:
        model = Author
        export_order = ('name', 'books')


class BookResource(resources.ModelResource):
    published = fields.Field(column_name='published_date')

    class Meta:
        model = Book
        exclude = ('imported', )


class CategoryResource(resources.ModelResource):

    class Meta:
        model = Category


class ProfileResource(resources.ModelResource):
    class Meta:
        model = Profile
        exclude = ('user', )


class WithDefaultResource(resources.ModelResource):
    class Meta:
        model = WithDefault
        fields = ('name',)


class HarshRussianWidget(widgets.CharWidget):
    def clean(self, value, row=None, *args, **kwargs):
        raise ValueError("Ова вриједност је страшна!")


class AuthorResourceWithCustomWidget(resources.ModelResource):

    class Meta:
        model = Author

    @classmethod
    def widget_from_django_field(cls, f, default=widgets.Widget):
        if f.name == 'name':
            return HarshRussianWidget
        result = default
        internal_type = f.get_internal_type() if callable(getattr(f, "get_internal_type", None)) else ""
        if internal_type in cls.WIDGETS_MAP:
            result = cls.WIDGETS_MAP[internal_type]
            if isinstance(result, six.string_types):
                result = getattr(cls, result)(f)
        return result


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

    def test_default(self):
        self.assertEquals(WithDefaultResource.fields['name'].clean({'name': ''}), 'foo_bar')

    def test_get_instance(self):
        instance_loader = self.resource._meta.instance_loader_class(
            self.resource)
        self.resource._meta.import_id_fields = ['id']
        instance = self.resource.get_instance(instance_loader,
                                              self.dataset.dict[0])
        self.assertEqual(instance, self.book)

    def test_get_instance_import_id_fields(self):

        class BookResource(resources.ModelResource):
            name = fields.Field(attribute='name', widget=widgets.CharWidget())

            class Meta:
                model = Book
                import_id_fields = ['name']

        resource = BookResource()
        instance_loader = resource._meta.instance_loader_class(resource)
        instance = resource.get_instance(instance_loader, self.dataset.dict[0])
        self.assertEqual(instance, self.book)

    def test_get_instance_with_missing_field_data(self):
        instance_loader = self.resource._meta.instance_loader_class(
            self.resource)
        # construct a dataset with a missing "id" column
        dataset = tablib.Dataset(headers=['name', 'author_email', 'price'])
        dataset.append(['Some book', 'test@example.com', "10.25"])
        with self.assertRaises(KeyError) as cm:
            self.resource.get_instance(instance_loader, dataset.dict[0])
        self.assertEqual(u"Column 'id' not found in dataset. Available columns "
                         "are: %s" % [u'name', u'author_email', u'price'],
                         cm.exception.args[0])

    def test_get_export_headers(self):
        headers = self.resource.get_export_headers()
        self.assertEqual(headers, ['published_date', 'id', 'name', 'author',
                                   'author_email', 'published_time', 'price',
                                   'categories', ])

    def test_export(self):
        dataset = self.resource.export(Book.objects.all())
        self.assertEqual(len(dataset), 1)

    def test_export_iterable(self):
        dataset = self.resource.export(list(Book.objects.all()))
        self.assertEqual(len(dataset), 1)

    def test_get_diff(self):
        diff = Diff(self.resource, self.book, False)
        book2 = Book(name="Some other book")
        diff.compare_with(self.resource, book2)
        html = diff.as_html()
        headers = self.resource.get_export_headers()
        self.assertEqual(html[headers.index('name')],
                         u'<span>Some </span><ins style="background:#e6ffe6;">'
                         u'other </ins><span>book</span>')
        self.assertFalse(html[headers.index('author_email')])

    @skip("See: https://github.com/django-import-export/django-import-export/issues/311")
    def test_get_diff_with_callable_related_manager(self):
        resource = AuthorResource()
        author = Author(name="Some author")
        author.save()
        author2 = Author(name="Some author")
        self.book.author = author
        self.book.save()
        diff = Diff(self.resource, author, False)
        diff.compare_with(self.resource, author2)
        html = diff.as_html()
        headers = resource.get_export_headers()
        self.assertEqual(html[headers.index('books')],
                         '<span>core.Book.None</span>')

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

    def test_import_data_raises_field_specific_validation_errors(self):
        resource = AuthorResource()
        dataset = tablib.Dataset(headers=['id', 'name', 'birthday'])
        dataset.append(['', 'A.A.Milne', '1882test-01-18'])

        result = resource.import_data(dataset, raise_errors=False)

        self.assertTrue(result.has_validation_errors())
        self.assertIs(result.rows[0].import_type, results.RowResult.IMPORT_TYPE_INVALID)
        self.assertIn('birthday', result.invalid_rows[0].field_specific_errors)

    def test_import_data_handles_widget_valueerrors_with_unicode_messages(self):
        resource = AuthorResourceWithCustomWidget()
        dataset = tablib.Dataset(headers=['id', 'name', 'birthday'])
        dataset.append(['', 'A.A.Milne', '1882-01-18'])

        result = resource.import_data(dataset, raise_errors=False)

        self.assertTrue(result.has_validation_errors())
        self.assertIs(result.rows[0].import_type, results.RowResult.IMPORT_TYPE_INVALID)
        self.assertEqual(
            result.invalid_rows[0].field_specific_errors['name'],
            ["Ова вриједност је страшна!"]
        )

    def test_model_validation_errors_not_raised_when_clean_model_instances_is_false(self):

        class TestResource(resources.ModelResource):
            class Meta:
                model = Author
                clean_model_instances = False

        resource = TestResource()
        dataset = tablib.Dataset(headers=['id', 'name'])
        dataset.append(['', '123'])

        result = resource.import_data(dataset, raise_errors=False)
        self.assertFalse(result.has_validation_errors())
        self.assertEqual(len(result.invalid_rows), 0)

    def test_model_validation_errors_raised_when_clean_model_instances_is_true(self):

        class TestResource(resources.ModelResource):
            class Meta:
                model = Author
                clean_model_instances = True

        resource = TestResource()
        dataset = tablib.Dataset(headers=['id', 'name'])
        dataset.append(['', '123'])

        result = resource.import_data(dataset, raise_errors=False)
        self.assertTrue(result.has_validation_errors())
        self.assertEqual(result.invalid_rows[0].error_count, 1)
        self.assertEqual(
            result.invalid_rows[0].field_specific_errors,
            {'name': ["'123' is not a valid value"]}
        )

    def test_known_invalid_fields_are_excluded_from_model_instance_cleaning(self):

        # The custom widget on the parent class should complain about
        # 'name' first, preventing Author.full_clean() from raising the
        # error as it does in the previous test

        class TestResource(AuthorResourceWithCustomWidget):
            class Meta:
                model = Author
                clean_model_instances = True

        resource = TestResource()
        dataset = tablib.Dataset(headers=['id', 'name'])
        dataset.append(['', '123'])

        result = resource.import_data(dataset, raise_errors=False)
        self.assertTrue(result.has_validation_errors())
        self.assertEqual(result.invalid_rows[0].error_count, 1)
        self.assertEqual(
            result.invalid_rows[0].field_specific_errors,
            {'name': ["Ова вриједност је страшна!"]}
        )

    def test_import_data_error_saving_model(self):
        row = list(self.dataset.pop())
        # set pk to something that would yield error
        row[0] = 'foo'
        self.dataset.append(row)
        result = self.resource.import_data(self.dataset, raise_errors=False)

        self.assertTrue(result.has_errors())
        self.assertTrue(result.rows[0].errors)
        actual = result.rows[0].errors[0].error
        self.assertIsInstance(actual, ValueError)
        self.assertIn("could not convert string to float", str(actual))

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

    def test_save_instance_with_dry_run_flag(self):
        class B(BookResource):
            def before_save_instance(self, instance, using_transactions, dry_run):
                super(B, self).before_save_instance(instance, using_transactions, dry_run)
                if dry_run:
                    self.before_save_instance_dry_run = True
                else:
                    self.before_save_instance_dry_run = False
            def save_instance(self, instance, using_transactions=True, dry_run=False):
                super(B, self).save_instance(instance, using_transactions, dry_run)
                if dry_run:
                    self.save_instance_dry_run = True
                else:
                    self.save_instance_dry_run = False
            def after_save_instance(self, instance, using_transactions, dry_run):
                super(B, self).after_save_instance(instance, using_transactions, dry_run)
                if dry_run:
                    self.after_save_instance_dry_run = True
                else:
                    self.after_save_instance_dry_run = False

        resource = B()
        resource.import_data(self.dataset, dry_run=True, raise_errors=True)
        self.assertTrue(resource.before_save_instance_dry_run)
        self.assertTrue(resource.save_instance_dry_run)
        self.assertTrue(resource.after_save_instance_dry_run)

        resource.import_data(self.dataset, dry_run=False, raise_errors=True)
        self.assertFalse(resource.before_save_instance_dry_run)
        self.assertFalse(resource.save_instance_dry_run)
        self.assertFalse(resource.after_save_instance_dry_run)

    def test_delete_instance_with_dry_run_flag(self):
        class B(BookResource):
            delete = fields.Field(widget=widgets.BooleanWidget())

            def for_delete(self, row, instance):
                return self.fields['delete'].clean(row)

            def before_delete_instance(self, instance, dry_run):
                super(B, self).before_delete_instance(instance, dry_run)
                if dry_run:
                    self.before_delete_instance_dry_run = True
                else:
                    self.before_delete_instance_dry_run = False

            def delete_instance(self, instance, using_transactions=True, dry_run=False):
                super(B, self).delete_instance(instance, using_transactions, dry_run)
                if dry_run:
                    self.delete_instance_dry_run = True
                else:
                    self.delete_instance_dry_run = False

            def after_delete_instance(self, instance, dry_run):
                super(B, self).after_delete_instance(instance, dry_run)
                if dry_run:
                    self.after_delete_instance_dry_run = True
                else:
                    self.after_delete_instance_dry_run = False

        resource = B()
        row = [self.book.pk, self.book.name, '1']
        dataset = tablib.Dataset(*[row], headers=['id', 'name', 'delete'])
        resource.import_data(dataset, dry_run=True, raise_errors=True)
        self.assertTrue(resource.before_delete_instance_dry_run)
        self.assertTrue(resource.delete_instance_dry_run)
        self.assertTrue(resource.after_delete_instance_dry_run)

        resource.import_data(dataset, dry_run=False, raise_errors=True)
        self.assertFalse(resource.before_delete_instance_dry_run)
        self.assertFalse(resource.delete_instance_dry_run)
        self.assertFalse(resource.after_delete_instance_dry_run)

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
        self.assertEqual(full_title, '%s by %s' % (self.book.name,
                                                   self.book.author.name))

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
            def before_import(self, dataset, using_transactions, dry_run, **kwargs):
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

    def test_before_import_raises_error(self):
        class B(BookResource):
            def before_import(self, dataset, using_transactions, dry_run, **kwargs):
                raise Exception('This is an invalid dataset')

        resource = B()
        with self.assertRaises(Exception) as cm:
            resource.import_data(self.dataset, raise_errors=True)
        self.assertEqual(u"This is an invalid dataset", cm.exception.args[0])

    def test_after_import_raises_error(self):
        class B(BookResource):
            def after_import(self, dataset, result, using_transactions, dry_run, **kwargs):
                raise Exception('This is an invalid dataset')

        resource = B()
        with self.assertRaises(Exception) as cm:
            resource.import_data(self.dataset, raise_errors=True)
        self.assertEqual(u"This is an invalid dataset", cm.exception.args[0])

    def test_link_to_nonexistent_field(self):
        with self.assertRaises(FieldDoesNotExist) as cm:
            class BrokenBook1(resources.ModelResource):
                class Meta:
                    model = Book
                    fields = ('nonexistent__invalid',)
        self.assertEqual("Book.nonexistent: Book has no field named 'nonexistent'",
                         cm.exception.args[0])

        with self.assertRaises(FieldDoesNotExist) as cm:
            class BrokenBook2(resources.ModelResource):
                class Meta:
                    model = Book
                    fields = ('author__nonexistent',)
        self.assertEqual("Book.author.nonexistent: Author has no field named "
                         "'nonexistent'", cm.exception.args[0])

    def test_link_to_nonrelation_field(self):
        with self.assertRaises(KeyError) as cm:
            class BrokenBook1(resources.ModelResource):
                class Meta:
                    model = Book
                    fields = ('published__invalid',)
        self.assertEqual("Book.published is not a relation",
                         cm.exception.args[0])

        with self.assertRaises(KeyError) as cm:
            class BrokenBook2(resources.ModelResource):
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
            def field_from_django_field(self, field_name, django_field,
                                        readonly):
                if field_name == 'published':
                    return {'sound': 'quack'}

        B()
        self.assertEqual({'sound': 'quack'}, B.fields['published'])

    def test_readonly_annotated_field_import_and_export(self):
        class B(BookResource):
            total_categories = fields.Field('total_categories', readonly=True)

            class Meta:
                model = Book
                skip_unchanged = True

        cat1 = Category.objects.create(name='Cat 1')
        self.book.categories.add(cat1)

        resource = B()

        # Verify that the annotated field is correctly exported
        dataset = resource.export(
            Book.objects.annotate(total_categories=Count('categories')))
        self.assertEqual(int(dataset.dict[0]['total_categories']), 1)

        # Verify that importing the annotated field raises no errors and that
        # the rows are skipped
        result = resource.import_data(dataset, raise_errors=True)
        self.assertFalse(result.has_errors())
        self.assertEqual(len(result.rows), len(dataset))
        self.assertEqual(
            result.rows[0].import_type, results.RowResult.IMPORT_TYPE_SKIP)

    def test_follow_relationship_for_modelresource(self):

        class EntryResource(resources.ModelResource):
            username = fields.Field(attribute='user__username', readonly=False)

            class Meta:
                model = Entry
                fields = ('id', )

            def after_save_instance(self, instance, using_transactions, dry_run):
                if not using_transactions and dry_run:
                    # we don't have transactions and we want to do a dry_run
                    pass
                else:
                    instance.user.save()

        user = User.objects.create(username='foo')
        entry = Entry.objects.create(user=user)
        row = [
            entry.pk,
            'bar',
        ]
        self.dataset = tablib.Dataset(headers=['id', 'username'])
        self.dataset.append(row)
        result = EntryResource().import_data(
            self.dataset, raise_errors=True, dry_run=False)
        self.assertFalse(result.has_errors())
        self.assertEquals(User.objects.get(pk=user.pk).username, 'bar')

    def test_import_data_dynamic_default_callable(self):

        class DynamicDefaultResource(resources.ModelResource):
            class Meta:
                model = WithDynamicDefault
                fields = ('id', 'name',)

        self.assertTrue(callable(DynamicDefaultResource.fields['name'].default))

        resource = DynamicDefaultResource()
        dataset = tablib.Dataset(headers=['id', 'name', ])
        dataset.append([1, None])
        dataset.append([2, None])
        resource.import_data(dataset, raise_errors=False)
        objs = WithDynamicDefault.objects.all()
        self.assertNotEqual(objs[0].name, objs[1].name)

    def test_float_field(self):
        #433
        class R(resources.ModelResource):
            class Meta:
                model = WithFloatField
        resource = R()
        dataset = tablib.Dataset(headers=['id', 'f', ])
        dataset.append([None, None])
        dataset.append([None, ''])
        resource.import_data(dataset, raise_errors=True)
        self.assertEqual(WithFloatField.objects.all()[0].f, None)
        self.assertEqual(WithFloatField.objects.all()[1].f, None)


class ModelResourceTransactionTest(TransactionTestCase):
    @skipUnlessDBFeature('supports_transactions')
    def test_m2m_import_with_transactions(self):
        resource = BookResource()
        cat1 = Category.objects.create(name='Cat 1')
        headers = ['id', 'name', 'categories']
        row = [None, 'FooBook', "%s" % cat1.pk]
        dataset = tablib.Dataset(row, headers=headers)

        result = resource.import_data(
            dataset, dry_run=True, use_transactions=True
        )

        row_diff = result.rows[0].diff
        fields = resource.get_fields()

        id_field = resource.fields['id']
        id_diff = row_diff[fields.index(id_field)]
        # id diff should exist because in rollbacked transaction
        # FooBook has been saved
        self.assertTrue(id_diff)

        category_field = resource.fields['categories']
        categories_diff = row_diff[fields.index(category_field)]
        self.assertEqual(strip_tags(categories_diff), force_text(cat1.pk))

        # check that it is really rollbacked
        self.assertFalse(Book.objects.filter(name='FooBook'))

    @skipUnlessDBFeature('supports_transactions')
    def test_m2m_import_with_transactions_error(self):
        resource = ProfileResource()
        headers = ['id', 'user']
        # 'user' is a required field, the database will raise an error.
        row = [None, None]
        dataset = tablib.Dataset(row, headers=headers)

        result = resource.import_data(
            dataset, dry_run=True, use_transactions=True
        )

        # Ensure the error raised by the database has been saved.
        self.assertTrue(result.has_errors())

        # Ensure the rollback has worked properly.
        self.assertEqual(Profile.objects.count(), 0)

    @skipUnlessDBFeature('supports_transactions')
    def test_integrity_error_rollback_on_savem2m(self):
        # savepoint_rollback() after an IntegrityError gives
        # TransactionManagementError (#399)
        class CategoryResourceRaisesIntegrityError(CategoryResource):
            def save_m2m(self, instance, *args, **kwargs):
                # force raising IntegrityError
                Category.objects.create(name=instance.name)

        resource = CategoryResourceRaisesIntegrityError()
        headers = ['id', 'name']
        rows = [
            [None, 'foo'],
        ]
        dataset = tablib.Dataset(*rows, headers=headers)
        result = resource.import_data(
            dataset,
            use_transactions=True,
        )
        self.assertTrue(result.has_errors())

    @skipUnlessDBFeature('supports_transactions')
    def test_multiple_database_errors(self):

        class CategoryResourceDbErrorsResource(CategoryResource):

            def before_import(self, *args, **kwargs):
                raise DatabaseError()

            def save_instance(self):
                raise DatabaseError()

        resource = CategoryResourceDbErrorsResource()
        headers = ['id', 'name']
        rows = [
            [None, 'foo'],
        ]
        dataset = tablib.Dataset(*rows, headers=headers)
        result = resource.import_data(
            dataset,
            use_transactions=True,
        )
        self.assertTrue(result.has_errors())


class ModelResourceFactoryTest(TestCase):

    def test_create(self):
        BookResource = resources.modelresource_factory(Book)
        self.assertIn('id', BookResource.fields)
        self.assertEqual(BookResource._meta.model, Book)


@skipUnless(
    'postgresql' in settings.DATABASES['default']['ENGINE'],
    'Run only against Postgres')
class PostgresTests(TransactionTestCase):
    # Make sure to start the sequences back at 1
    reset_sequences = True

    def test_create_object_after_importing_dataset_with_id(self):
        dataset = tablib.Dataset(headers=['id', 'name'])
        dataset.append([1, 'Some book'])
        resource = BookResource()
        result = resource.import_data(dataset)
        self.assertFalse(result.has_errors())
        try:
            Book.objects.create(name='Some other book')
        except IntegrityError:
            self.fail('IntegrityError was raised.')

    def test_collect_failed_rows(self):
        resource = ProfileResource()
        headers = ['id', 'user']
        # 'user' is a required field, the database will raise an error.
        row = [None, None]
        dataset = tablib.Dataset(row, headers=headers)
        result = resource.import_data(
            dataset, dry_run=True, use_transactions=True,
            collect_failed_rows=True,
        )
        self.assertEqual(
            result.failed_dataset.headers,
            [u'id', u'user', u'Error']
        )
        self.assertEqual(len(result.failed_dataset), 1)
        # We can't check the error message because it's package- and version-dependent


if 'postgresql' in settings.DATABASES['default']['ENGINE']:
    from django.contrib.postgres.fields import ArrayField
    from django.db import models

    class BookWithChapters(models.Model):
        name = models.CharField('Book name', max_length=100)
        chapters = ArrayField(models.CharField(max_length=100), default=list)

    class ArrayFieldTest(TestCase):
        fixtures = []

        def setUp(self):
            pass

        def test_arrayfield(self):
            dataset_headers = ["id", "name", "chapters"]
            chapters = ["Introduction", "Middle Chapter", "Ending"]
            dataset_row = ["1", "Book With Chapters", ",".join(chapters)]
            dataset = tablib.Dataset(headers=dataset_headers)
            dataset.append(dataset_row)
            book_with_chapters_resource = resources.modelresource_factory(model=BookWithChapters)()
            result = book_with_chapters_resource.import_data(dataset, dry_run=False)
            self.assertFalse(result.has_errors())
            book_with_chapters = list(BookWithChapters.objects.all())[0]
            self.assertListEqual(book_with_chapters.chapters, chapters)


class ForeignKeyWidgetFollowRelationship(TestCase):
    def setUp(self):
        self.user = User.objects.create(username='foo')
        self.role = Role.objects.create(user=self.user)
        self.person = Person.objects.create(role=self.role)

    def test_export(self):
        class MyPersonResource(resources.ModelResource):
            role = fields.Field(
                column_name='role',
                attribute='role',
                widget=widgets.ForeignKeyWidget(Role, field='user__username')
            )

            class Meta:
                model = Person
                fields = ['id', 'role']

        resource = MyPersonResource()
        dataset = resource.export(Person.objects.all())
        self.assertEqual(len(dataset), 1)
        self.assertEqual(dataset[0][0], 'foo')

        self.role.user = None
        self.role.save()

        resource = MyPersonResource()
        dataset = resource.export(Person.objects.all())
        self.assertEqual(len(dataset), 1)
        self.assertEqual(dataset[0][0], None)


class ManyRelatedManagerDiffTest(TestCase):
    fixtures = ["category", "book"]

    def setUp(self):
        pass

    def test_related_manager_diff(self):
        dataset_headers = ["id", "name", "categories"]
        dataset_row = ["1", "Test Book", "1"]
        original_dataset = tablib.Dataset(headers=dataset_headers)
        original_dataset.append(dataset_row)
        dataset_row[2] = "2"
        changed_dataset = tablib.Dataset(headers=dataset_headers)
        changed_dataset.append(dataset_row)

        book_resource = BookResource()
        export_headers = book_resource.get_export_headers()

        add_result = book_resource.import_data(original_dataset, dry_run=False)
        expected_value = u'<ins style="background:#e6ffe6;">1</ins>'
        self.check_value(add_result, export_headers, expected_value)
        change_result = book_resource.import_data(changed_dataset, dry_run=False)
        expected_value = u'<del style="background:#ffe6e6;">1</del><ins style="background:#e6ffe6;">2</ins>'
        self.check_value(change_result, export_headers, expected_value)

    def check_value(self, result, export_headers, expected_value):
        self.assertEqual(len(result.rows), 1)
        diff = result.rows[0].diff
        self.assertEqual(diff[export_headers.index("categories")],
                         expected_value)
