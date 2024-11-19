from unittest.mock import patch

from core.models import Book
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase
from tablib import Dataset

from import_export.results import Error, InvalidRow, Result, RowResult


class ErrorTest(SimpleTestCase):
    def test_repr_no_details(self):
        try:
            1 / 0
        except Exception as exc:
            error = Error(exc)

        self.assertEqual(repr(error), "<Error: ZeroDivisionError('division by zero')>")

    def test_repr_all_details(self):
        try:
            1 / 0
        except Exception as exc:
            error = Error(exc, row=1, number=2)

        self.assertEqual(
            repr(error),
            "<Error: ZeroDivisionError('division by zero') at row 1 at number 2>",
        )

    def test_traceback(self):
        try:
            1 / 0
        except Exception as exc:
            error = Error(exc)

        self.assertTrue(
            error.traceback.startswith("Traceback (most recent call last):\n")
        )
        self.assertIn(
            "ZeroDivisionError: division by zero\n",
            error.traceback,
        )


class InvalidRowTest(SimpleTestCase):
    def test_repr(self):
        try:
            raise ValidationError(message="invalid row")
        except ValidationError as exc:
            error = InvalidRow(validation_error=exc, number=1, values={})

        self.assertEqual(
            repr(error),
            "<InvalidRow(row=1, error=ValidationError(['invalid row']),"
            " error_count=1)>",
        )


class ResultTest(SimpleTestCase):
    def setUp(self):
        self.result = Result()
        headers = ["id", "book_name"]
        rows = [(1, "Some book")]
        self.dataset = Dataset(*rows, headers=headers)

    def test_add_dataset_headers(self):
        target = ["some_header", "Error"]
        self.result.add_dataset_headers(["some_header"])
        self.assertEqual(target, self.result.failed_dataset.headers)

    def test_add_dataset_headers_empty_list(self):
        target = ["Error"]
        self.result.add_dataset_headers([])
        self.assertEqual(target, self.result.failed_dataset.headers)

    def test_add_dataset_headers_None(self):
        target = ["Error"]
        self.result.add_dataset_headers(None)
        self.assertEqual(target, self.result.failed_dataset.headers)

    def test_result_append_failed_row_with_ValidationError(self):
        target = [[1, "Some book", "['some error']"]]
        self.result.append_failed_row(
            self.dataset.dict[0], ValidationError("some error")
        )
        self.assertEqual(target, self.result.failed_dataset.dict)

    def test_result_append_failed_row_with_wrapped_error(self):
        target = [[1, "Some book", "['some error']"]]
        row_result = RowResult()
        error = Error(ValidationError("some error"))
        row_result.errors = [error]
        self.result.append_failed_row(self.dataset.dict[0], row_result.errors[0])
        self.assertEqual(target, self.result.failed_dataset.dict)

    def test_add_instance_info_null_instance(self):
        row_result = RowResult()
        row_result.add_instance_info(None)
        self.assertEqual(None, row_result.object_id)
        self.assertEqual(None, row_result.object_repr)

    def test_add_instance_info_no_instance_pk(self):
        row_result = RowResult()
        row_result.add_instance_info(Book())
        self.assertEqual(None, row_result.object_id)
        self.assertEqual("", row_result.object_repr)

    def test_add_instance_info(self):
        row_result = RowResult()
        row_result.add_instance_info(Book(pk=1, name="some book"))
        self.assertEqual(1, row_result.object_id)
        self.assertEqual("some book", row_result.object_repr)

    @patch("import_export.results.logger")
    def test_add_instance_info_instance_unserializable(self, mock_logger):
        # issue 1763
        class UnserializableBook:
            # will raise TypeError
            def __str__(self):
                return None

        row_result = RowResult()
        row_result.add_instance_info(UnserializableBook())
        mock_logger.debug.assert_called_with(
            "call to force_str() on instance failed: "
            "__str__ returned non-string (type NoneType)"
        )
        self.assertEqual(None, row_result.object_repr)

    def test_is_new(self):
        row_result = RowResult()
        self.assertFalse(row_result.is_new())
        row_result.import_type = RowResult.IMPORT_TYPE_NEW
        self.assertTrue(row_result.is_new())
        self.assertTrue(row_result.is_valid())

    def test_is_update(self):
        row_result = RowResult()
        self.assertFalse(row_result.is_update())
        row_result.import_type = RowResult.IMPORT_TYPE_UPDATE
        self.assertTrue(row_result.is_update())
        self.assertTrue(row_result.is_valid())

    def test_is_skip(self):
        row_result = RowResult()
        self.assertFalse(row_result.is_skip())
        row_result.import_type = RowResult.IMPORT_TYPE_SKIP
        self.assertTrue(row_result.is_skip())
        self.assertTrue(row_result.is_valid())

    def test_is_delete(self):
        row_result = RowResult()
        self.assertFalse(row_result.is_delete())
        row_result.import_type = RowResult.IMPORT_TYPE_DELETE
        self.assertTrue(row_result.is_delete())
        self.assertTrue(row_result.is_valid())

    def test_is_error(self):
        row_result = RowResult()
        self.assertFalse(row_result.is_error())
        row_result.import_type = RowResult.IMPORT_TYPE_ERROR
        self.assertTrue(row_result.is_error())
        self.assertFalse(row_result.is_valid())

    def test_is_invalid(self):
        row_result = RowResult()
        self.assertFalse(row_result.is_invalid())
        row_result.import_type = RowResult.IMPORT_TYPE_INVALID
        self.assertTrue(row_result.is_invalid())
        self.assertFalse(row_result.is_valid())
