import tablib
from django.test import TestCase

from import_export import resources

from ....models import Book


class AfterImportComparisonTest(TestCase):
    class BookResource(resources.ModelResource):
        is_published = False

        def after_import_row(self, row, row_result, **kwargs):
            if (
                getattr(row_result.original, "published") is None
                and getattr(row_result.instance, "published") is not None
            ):
                self.is_published = True

        class Meta:
            model = Book
            store_instance = True

    def setUp(self):
        super().setUp()
        self.resource = AfterImportComparisonTest.BookResource()
        self.book = Book.objects.create(name="Some book")
        self.dataset = tablib.Dataset(headers=["id", "name", "published"])
        row = [self.book.pk, "Some book", "2023-05-09"]
        self.dataset.append(row)

    def test_after_import_row_check_for_change(self):
        # issue 1583 - assert that `original` object is available to after_import_row()
        self.resource.import_data(self.dataset, raise_errors=True)
        self.assertTrue(self.resource.is_published)
