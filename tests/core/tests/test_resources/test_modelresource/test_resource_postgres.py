import json
import sys
from unittest import skipUnless

import tablib
from core.models import Book
from core.tests.resources import BookResource
from django.conf import settings
from django.db import IntegrityError, connection
from django.db.models import CharField
from django.test import TestCase, TransactionTestCase

from import_export import fields, resources, widgets


class ModelResourcePostgresModuleLoadTest(TestCase):
    pg_module_name = "django.contrib.postgres.fields"

    class ImportRaiser:
        def find_spec(self, fullname, path, target=None):
            if fullname == ModelResourcePostgresModuleLoadTest.pg_module_name:
                # we get here if the module is not loaded and not in sys.modules
                raise ImportError()

    def setUp(self):
        super().setUp()
        self.resource = BookResource()
        if self.pg_module_name in sys.modules:
            self.pg_modules = sys.modules[self.pg_module_name]
            del sys.modules[self.pg_module_name]

    def tearDown(self):
        super().tearDown()
        sys.modules[self.pg_module_name] = self.pg_modules

    def test_widget_from_django_field_cannot_import_postgres(self):
        # test that default widget is returned if postgres extensions
        # are not present
        sys.meta_path.insert(0, self.ImportRaiser())

        f = fields.Field()
        res = self.resource.widget_from_django_field(f)
        self.assertEqual(widgets.Widget, res)


@skipUnless(
    "postgresql" in settings.DATABASES["default"]["ENGINE"], "Run only against Postgres"
)
class PostgresTests(TransactionTestCase):
    # Make sure to start the sequences back at 1
    reset_sequences = True

    def test_create_object_after_importing_dataset_with_id(self):
        dataset = tablib.Dataset(headers=["id", "name"])
        dataset.append([1, "Some book"])
        resource = BookResource()
        result = resource.import_data(dataset)
        self.assertFalse(result.has_errors())
        try:
            Book.objects.create(name="Some other book")
        except IntegrityError:
            self.fail("IntegrityError was raised.")

    def test_widget_from_django_field_for_ArrayField_returns_SimpleArrayWidget(self):
        f = ArrayField(CharField)
        resource = BookResource()
        res = resource.widget_from_django_field(f)
        self.assertEqual(widgets.SimpleArrayWidget, res)

    def test_sequence_reset_does_not_rewind_concurrently_advanced_sequence(self):
        # Regression test for #2166: after_import() must not rewind the
        # sequence below a value already issued to a "concurrent" caller
        # (simulated here by manually advancing the sequence past the
        # table's current max id before running the import).
        dataset = tablib.Dataset(headers=["id", "name"])
        dataset.append([1, "Some book"])
        resource = BookResource()
        result = resource.import_data(dataset)
        self.assertFalse(result.has_errors())

        # Simulate a concurrent transaction that has already called
        # nextval() several times beyond the current max(id), e.g. via
        # in-flight INSERTs that have not yet been committed/visible.
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT setval(pg_get_serial_sequence('core_book','id'), 100)"
            )

        dataset2 = tablib.Dataset(headers=["id", "name"])
        dataset2.append([2, "Another book"])
        result2 = resource.import_data(dataset2)
        self.assertFalse(result2.has_errors())

        # The sequence must not have been rewound below the concurrently
        # advanced value: a subsequent auto-assigned insert must succeed.
        try:
            Book.objects.create(name="Some other book")
        except IntegrityError:
            self.fail(
                "IntegrityError was raised: sequence was rewound below a "
                "value already issued to a concurrent caller."
            )


class SequenceResetSqlUnitTests(TestCase):
    """
    Unit tests for the concurrency-safe sequence reset SQL builder.

    These run regardless of the configured database backend (the code
    under test only builds a SQL string; it does not execute it), so
    they exercise the fix even when Postgres isn't available in this
    environment.
    """

    def test_generated_sql_uses_greatest_and_does_not_rewind(self):
        from unittest.mock import Mock

        pg_connection = Mock()
        pg_connection.ops.quote_name = lambda name: '"%s"' % name

        sql = resources.ModelResource._get_safe_postgres_sequence_reset_sql(
            pg_connection, Book
        )
        self.assertEqual(1, len(sql))
        statement = sql[0]
        self.assertIn("GREATEST(", statement)
        self.assertIn("pg_sequence_last_value(", statement)
        self.assertIn("setval(", statement)


if "postgresql" in settings.DATABASES["default"]["ENGINE"]:
    from django.contrib.postgres.fields import ArrayField
    from django.db import models

    class BookWithChapters(models.Model):
        name = models.CharField("Book name", max_length=100)
        chapters = ArrayField(models.CharField(max_length=100), default=list)
        data = models.JSONField(null=True)

    class BookWithChapterNumbers(models.Model):
        name = models.CharField("Book name", max_length=100)
        chapter_numbers = ArrayField(models.PositiveSmallIntegerField(), default=list)

    class BookWithChaptersResource(resources.ModelResource):
        class Meta:
            model = BookWithChapters
            fields = (
                "id",
                "name",
                "chapters",
                "data",
            )

    class BookWithChapterNumbersResource(resources.ModelResource):
        class Meta:
            model = BookWithChapterNumbers
            fields = (
                "id",
                "name",
                "chapter_numbers",
            )

    class TestExportArrayField(TestCase):
        def test_exports_array_field(self):
            dataset_headers = ["id", "name", "chapters"]
            chapters = ["Introduction", "Middle Chapter", "Ending"]
            dataset_row = ["1", "Book With Chapters", ",".join(chapters)]
            dataset = tablib.Dataset(headers=dataset_headers)
            dataset.append(dataset_row)
            book_with_chapters_resource = resources.modelresource_factory(
                model=BookWithChapters
            )()
            result = book_with_chapters_resource.import_data(dataset, dry_run=False)

            self.assertFalse(result.has_errors())
            book_with_chapters = list(BookWithChapters.objects.all())[0]
            self.assertListEqual(book_with_chapters.chapters, chapters)

    class TestImportArrayField(TestCase):
        def setUp(self):
            self.resource = BookWithChaptersResource()
            self.chapters = ["Introduction", "Middle Chapter", "Ending"]
            self.book = BookWithChapters.objects.create(name="foo")
            self.dataset = tablib.Dataset(headers=["id", "name", "chapters"])
            row = [self.book.id, "Some book", ",".join(self.chapters)]
            self.dataset.append(row)

        def test_import_of_data_with_array(self):
            self.assertListEqual(self.book.chapters, [])
            result = self.resource.import_data(self.dataset, raise_errors=True)

            self.assertFalse(result.has_errors())
            self.assertEqual(len(result.rows), 1)

            self.book.refresh_from_db()
            self.assertEqual(self.book.chapters, self.chapters)

    class TestImportIntArrayField(TestCase):
        def setUp(self):
            self.resource = BookWithChapterNumbersResource()
            self.chapter_numbers = [1, 2, 3]
            self.book = BookWithChapterNumbers.objects.create(
                name="foo", chapter_numbers=[]
            )
            self.dataset = tablib.Dataset(
                *[(1, "some book", "1,2,3")], headers=["id", "name", "chapter_numbers"]
            )

        def test_import_of_data_with_int_array(self):
            # issue #1495
            self.assertListEqual(self.book.chapter_numbers, [])
            result = self.resource.import_data(self.dataset, raise_errors=True)

            self.assertFalse(result.has_errors())
            self.assertEqual(len(result.rows), 1)

            self.book.refresh_from_db()
            self.assertEqual(self.book.chapter_numbers, self.chapter_numbers)

    class TestExportJsonField(TestCase):
        def setUp(self):
            self.json_data = {"some_key": "some_value"}
            self.book = BookWithChapters.objects.create(name="foo", data=self.json_data)

        def test_export_field_with_appropriate_format(self):
            resource = resources.modelresource_factory(model=BookWithChapters)()
            result = resource.export(BookWithChapters.objects.all())
            self.assertEqual(result[0][3], json.dumps(self.json_data))

    class TestImportJsonField(TestCase):
        def setUp(self):
            self.resource = BookWithChaptersResource()
            self.data = {"some_key": "some_value"}
            self.json_data = json.dumps(self.data)
            self.book = BookWithChapters.objects.create(name="foo")
            self.dataset = tablib.Dataset(headers=["id", "name", "data"])
            row = [self.book.id, "Some book", self.json_data]
            self.dataset.append(row)

        def test_sets_json_data_when_model_field_is_empty(self):
            self.assertIsNone(self.book.data)
            result = self.resource.import_data(self.dataset, raise_errors=True)

            self.assertFalse(result.has_errors())
            self.assertEqual(len(result.rows), 1)

            self.book.refresh_from_db()
            self.assertEqual(self.book.data, self.data)
