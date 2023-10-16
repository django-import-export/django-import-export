from core.models import Book
from django.core.exceptions import ValidationError
from django.test.testcases import TestCase
from tablib import Dataset

from import_export.results import Error, Result, RowResult


class ResultTest(TestCase):
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
        class BookWithObjectRepr(Book):
            def __str__(self):
                return self.name

        row_result = RowResult()
        row_result.add_instance_info(BookWithObjectRepr(pk=1, name="some book"))
        self.assertEqual(1, row_result.object_id)
        self.assertEqual("some book", row_result.object_repr)
