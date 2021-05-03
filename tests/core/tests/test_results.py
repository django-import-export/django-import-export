from django.core.exceptions import ValidationError
from django.test.testcases import TestCase
from tablib import Dataset

from import_export.results import Error, Result, RowResult


class ResultTest(TestCase):

    def setUp(self):
        self.result = Result()
        headers = ['id', 'book_name']
        rows = [(1, 'Some book')]
        self.dataset = Dataset(*rows, headers=headers)

    def test_add_dataset_headers(self):
        target = ['Error']
        self.result.add_dataset_headers([])
        self.assertEqual(target, self.result.failed_dataset.headers)

    def test_result_append_failed_row_with_ValidationError(self):
        target = [[1, 'Some book', "['some error']"]]
        self.result.append_failed_row(self.dataset.dict[0], ValidationError('some error'))
        self.assertEqual(target, self.result.failed_dataset.dict)

    def test_result_append_failed_row_with_wrapped_error(self):
        target = [[1, 'Some book', "['some error']"]]
        row_result = RowResult()
        error = Error(ValidationError('some error'))
        row_result.errors = [error]
        self.result.append_failed_row(self.dataset.dict[0], row_result.errors[0])
        self.assertEqual(target, self.result.failed_dataset.dict)