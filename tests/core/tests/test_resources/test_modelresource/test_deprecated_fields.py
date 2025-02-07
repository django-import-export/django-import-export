import warnings

import tablib
from core.models import Book
from core.tests.resources import BookResource
from django.test import TestCase

from import_export import resources


class DeprecatedMethodTest(TestCase):
    """
    These tests relate to renamed methods in v4.
    The tests can be removed when the deprecated methods are removed.
    """

    def setUp(self):
        rows = [
            ["1", "Ulysses"],
        ]
        self.dataset = tablib.Dataset(*rows, headers=["id", "name"])
        self.obj = Book.objects.create(id=1, name="Ulysses")

    def test_import_obj_renamed(self):
        resource = BookResource()
        with self.assertWarns(
            DeprecationWarning,
        ):
            resource.import_obj(self.obj, self.dataset, dry_run=True)

    def test_import_obj_passes_params(self):
        class MyBookResource(resources.ModelResource):
            def import_instance(self, instance, row, **kwargs):
                self.kwargs = kwargs

            class Meta:
                model = Book

        resource = MyBookResource()
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            resource.import_obj(self.obj, self.dataset, True)
        self.assertTrue(resource.kwargs["dry_run"])

    def test_after_import_instance_renamed(self):
        resource = BookResource()
        with self.assertWarns(
            DeprecationWarning,
        ):
            resource.after_import_instance(self.obj, True, row_number=1)

    def test_after_import_instance_passes_params(self):
        class MyBookResource(resources.ModelResource):
            def after_init_instance(self, instance, new, row, **kwargs):
                self.kwargs = kwargs

            class Meta:
                model = Book

        resource = MyBookResource()
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            resource.after_import_instance(self.obj, True, row_number=1)
        self.assertEqual(1, resource.kwargs["row_number"])

    def test_get_fields_deprecated(self):
        resource = BookResource()
        with self.assertWarnsRegex(
            DeprecationWarning,
            r"The 'get_fields\(\)' method is deprecated "
            "and will be removed in a future release",
        ):
            fields = resource.get_fields()

        self.assertEqual(
            {f.column_name for f in fields},
            {
                "added",
                "author",
                "author_email",
                "categories",
                "id",
                "name",
                "price",
                "published_date",
                "published_time",
            },
        )
