import sys
from unittest import skipUnless

import tablib
from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import IntegrityError
from django.db.models import CharField
from django.test import TestCase, TransactionTestCase

from import_export import fields, resources, widgets

from ....models import Book


class BookResource(resources.ModelResource):
    published = fields.Field(column_name="published_date")

    class Meta:
        model = Book
        exclude = ("imported",)


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
