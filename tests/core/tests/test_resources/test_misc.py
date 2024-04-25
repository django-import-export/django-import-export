import tablib
from core.models import Author, Book, Category
from django.test import TestCase

from import_export import resources, results


class RawValueTest(TestCase):
    def setUp(self):
        class _BookResource(resources.ModelResource):
            class Meta:
                model = Book
                store_row_values = True

        self.resource = _BookResource()

        self.book = Book.objects.create(name="Some book")
        self.dataset = tablib.Dataset(headers=["id", "name", "author_email", "price"])
        row = [self.book.pk, "Some book", "test@example.com", "10.25"]
        self.dataset.append(row)

    def test_import_data(self):
        result = self.resource.import_data(self.dataset, raise_errors=True)

        self.assertFalse(result.has_errors())
        self.assertEqual(len(result.rows), 1)
        self.assertTrue(result.rows[0].diff)
        self.assertEqual(
            result.rows[0].import_type, results.RowResult.IMPORT_TYPE_UPDATE
        )
        self.assertEqual(result.rows[0].row_values.get("name"), "Some book")
        self.assertEqual(
            result.rows[0].row_values.get("author_email"), "test@example.com"
        )
        self.assertEqual(result.rows[0].row_values.get("price"), "10.25")


class ResourcesHelperFunctionsTest(TestCase):
    """
    Test the helper functions in resources.
    """

    def test_has_natural_foreign_key(self):
        """
        Ensure that resources.has_natural_foreign_key detects correctly
        whether a model has a natural foreign key
        """
        cases = {Book: True, Author: True, Category: False}

        for model, expected_result in cases.items():
            self.assertEqual(resources.has_natural_foreign_key(model), expected_result)
