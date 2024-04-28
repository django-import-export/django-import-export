from decimal import InvalidOperation

import tablib
from core.models import Author, Book
from core.tests.resources import AuthorResourceWithCustomWidget, BookResource
from django.test import TestCase

from import_export import resources, results


class DataHandlingTest(TestCase):
    def setUp(self):
        self.resource = BookResource()
        self.book = Book.objects.create(name="Some book")
        self.dataset = tablib.Dataset(headers=["id", "name", "author_email", "price"])
        row = [self.book.pk, "Some book", "test@example.com", "10.25"]
        self.dataset.append(row)

    def test_import_data_handles_widget_valueerrors_with_unicode_messages(self):
        resource = AuthorResourceWithCustomWidget()
        dataset = tablib.Dataset(headers=["id", "name", "birthday"])
        dataset.append(["", "A.A.Milne", "1882-01-18"])

        result = resource.import_data(dataset, raise_errors=False)

        self.assertTrue(result.has_validation_errors())
        self.assertIs(result.rows[0].import_type, results.RowResult.IMPORT_TYPE_INVALID)
        self.assertEqual(
            result.invalid_rows[0].field_specific_errors["name"],
            ["Ова вриједност је страшна!"],
        )

    def test_model_validation_errors_not_raised_when_clean_model_instances_is_false(
        self,
    ):
        class TestResource(resources.ModelResource):
            class Meta:
                model = Author
                clean_model_instances = False

        resource = TestResource()
        dataset = tablib.Dataset(headers=["id", "name"])
        dataset.append(["", "123"])

        result = resource.import_data(dataset, raise_errors=False)
        self.assertFalse(result.has_validation_errors())
        self.assertEqual(len(result.invalid_rows), 0)

    def test_model_validation_errors_raised_when_clean_model_instances_is_true(self):
        class TestResource(resources.ModelResource):
            class Meta:
                model = Author
                clean_model_instances = True
                export_order = ["id", "name", "birthday"]

        # create test dataset
        # NOTE: column order is deliberately strange
        dataset = tablib.Dataset(headers=["name", "id"])
        dataset.append(["123", "1"])

        # run import_data()
        resource = TestResource()
        result = resource.import_data(dataset, raise_errors=False)

        # check has_validation_errors()
        self.assertTrue(result.has_validation_errors())

        # check the invalid row itself
        invalid_row = result.invalid_rows[0]
        self.assertEqual(invalid_row.error_count, 1)
        self.assertEqual(
            invalid_row.field_specific_errors, {"name": ["'123' is not a valid value"]}
        )
        # diff_header and invalid_row.values should match too
        self.assertEqual(result.diff_headers, ["id", "name", "birthday"])
        self.assertEqual(invalid_row.values, ("1", "123", "---"))

    def test_known_invalid_fields_are_excluded_from_model_instance_cleaning(self):
        # The custom widget on the parent class should complain about
        # 'name' first, preventing Author.full_clean() from raising the
        # error as it does in the previous test

        class TestResource(AuthorResourceWithCustomWidget):
            class Meta:
                model = Author
                clean_model_instances = True

        resource = TestResource()
        dataset = tablib.Dataset(headers=["id", "name"])
        dataset.append(["", "123"])

        result = resource.import_data(dataset, raise_errors=False)
        self.assertTrue(result.has_validation_errors())
        self.assertEqual(result.invalid_rows[0].error_count, 1)
        self.assertEqual(
            result.invalid_rows[0].field_specific_errors,
            {"name": ["Ова вриједност је страшна!"]},
        )

    def test_import_data_error_saving_model(self):
        row = list(self.dataset.pop())
        # set pk to something that would yield error
        row[0] = "foo"
        self.dataset.append(row)
        result = self.resource.import_data(self.dataset, raise_errors=False)

        self.assertTrue(result.has_errors())
        self.assertTrue(result.rows[0].errors)
        actual = result.rows[0].errors[0].error
        self.assertIsInstance(actual, (ValueError, InvalidOperation))
        self.assertIn(
            str(actual),
            {
                "could not convert string to float",
                "[<class 'decimal.ConversionSyntax'>]",
                "Invalid literal for Decimal: 'foo'",
            },
        )
