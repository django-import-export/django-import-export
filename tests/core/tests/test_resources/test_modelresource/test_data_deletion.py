from unittest import mock

import tablib
from core.models import Book
from core.tests.resources import BookResource
from django.test import TestCase

from import_export import fields, results, widgets


class DataDeletionDryRunTest(TestCase):
    def setUp(self):
        self.resource = BookResource()
        self.book = Book.objects.create(name="Some book")
        self.dataset = tablib.Dataset(headers=["id", "name", "author_email", "price"])
        row = [self.book.pk, "Some book", "test@example.com", "10.25"]
        self.dataset.append(row)

    def test_import_data_delete(self):
        class B(BookResource):
            delete = fields.Field(widget=widgets.BooleanWidget())

            def for_delete(self, row, instance):
                return self.fields["delete"].clean(row)

        row = [self.book.pk, self.book.name, "1"]
        dataset = tablib.Dataset(*[row], headers=["id", "name", "delete"])
        result = B().import_data(dataset, raise_errors=True)
        self.assertFalse(result.has_errors())
        self.assertEqual(
            result.rows[0].import_type, results.RowResult.IMPORT_TYPE_DELETE
        )
        self.assertFalse(Book.objects.filter(pk=self.book.pk))
        self.assertIsNone(result.rows[0].instance)
        self.assertIsNone(result.rows[0].original)

    def test_import_data_delete_store_instance(self):
        class B(BookResource):
            delete = fields.Field(widget=widgets.BooleanWidget())

            def for_delete(self, row, instance):
                return self.fields["delete"].clean(row)

            class Meta:
                store_instance = True

        row = [self.book.pk, self.book.name, "1"]
        dataset = tablib.Dataset(*[row], headers=["id", "name", "delete"])
        result = B().import_data(dataset, raise_errors=True)
        self.assertEqual(
            result.rows[0].import_type, results.RowResult.IMPORT_TYPE_DELETE
        )
        self.assertIsNotNone(result.rows[0].instance)

    def test_save_instance_with_dry_run_flag(self):
        class B(BookResource):
            def before_save_instance(self, instance, row, **kwargs):
                super().before_save_instance(instance, row, **kwargs)
                dry_run = kwargs.get("dry_run", False)
                if dry_run:
                    self.before_save_instance_dry_run = True
                else:
                    self.before_save_instance_dry_run = False

            def save_instance(self, instance, new, row, **kwargs):
                super().save_instance(instance, new, row, **kwargs)
                dry_run = kwargs.get("dry_run", False)
                if dry_run:
                    self.save_instance_dry_run = True
                else:
                    self.save_instance_dry_run = False

            def after_save_instance(self, instance, row, **kwargs):
                super().after_save_instance(instance, row, **kwargs)
                dry_run = kwargs.get("dry_run", False)
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

    @mock.patch("core.models.Book.save")
    def test_save_instance_noop(self, mock_book):
        book = Book.objects.first()
        self.resource.save_instance(
            book, False, None, using_transactions=False, dry_run=True
        )
        self.assertEqual(0, mock_book.call_count)

    @mock.patch("core.models.Book.save")
    def test_delete_instance_noop(self, mock_book):
        book = Book.objects.first()
        self.resource.delete_instance(
            book, None, using_transactions=False, dry_run=True
        )
        self.assertEqual(0, mock_book.call_count)

    def test_delete_instance_with_dry_run_flag(self):
        class B(BookResource):
            delete = fields.Field(widget=widgets.BooleanWidget())

            def for_delete(self, row, instance):
                return self.fields["delete"].clean(row)

            def before_delete_instance(self, instance, row, **kwargs):
                super().before_delete_instance(instance, row, **kwargs)
                dry_run = kwargs.get("dry_run", False)
                if dry_run:
                    self.before_delete_instance_dry_run = True
                else:
                    self.before_delete_instance_dry_run = False

            def delete_instance(self, instance, row, **kwargs):
                super().delete_instance(instance, row, **kwargs)
                dry_run = kwargs.get("dry_run", False)
                if dry_run:
                    self.delete_instance_dry_run = True
                else:
                    self.delete_instance_dry_run = False

            def after_delete_instance(self, instance, row, **kwargs):
                super().after_delete_instance(instance, row, **kwargs)
                dry_run = kwargs.get("dry_run", False)
                if dry_run:
                    self.after_delete_instance_dry_run = True
                else:
                    self.after_delete_instance_dry_run = False

        resource = B()
        row = [self.book.pk, self.book.name, "1"]
        dataset = tablib.Dataset(*[row], headers=["id", "name", "delete"])
        resource.import_data(dataset, dry_run=True, raise_errors=True)
        self.assertTrue(resource.before_delete_instance_dry_run)
        self.assertTrue(resource.delete_instance_dry_run)
        self.assertTrue(resource.after_delete_instance_dry_run)

        resource.import_data(dataset, dry_run=False, raise_errors=True)
        self.assertFalse(resource.before_delete_instance_dry_run)
        self.assertFalse(resource.delete_instance_dry_run)
        self.assertFalse(resource.after_delete_instance_dry_run)
