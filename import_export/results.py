from __future__ import unicode_literals

from collections import OrderedDict

from django.core.exceptions import NON_FIELD_ERRORS

from tablib import Dataset


class Error(object):
    def __init__(self, error, traceback=None, row=None):
        self.error = error
        self.traceback = traceback
        self.row = row


class RowResult(object):
    IMPORT_TYPE_UPDATE = 'update'
    IMPORT_TYPE_NEW = 'new'
    IMPORT_TYPE_DELETE = 'delete'
    IMPORT_TYPE_SKIP = 'skip'
    IMPORT_TYPE_ERROR = 'error'
    IMPORT_TYPE_INVALID = 'invalid'

    valid_import_types = frozenset([
        IMPORT_TYPE_NEW,
        IMPORT_TYPE_UPDATE,
        IMPORT_TYPE_DELETE,
        IMPORT_TYPE_SKIP,
    ])

    def __init__(self):
        self.errors = []
        self.validation_error = None
        self.diff = None
        self.import_type = None
        self.raw_values = {}


class InvalidRow(object):
    """A row that resulted in one or more ``ValidationError`` being raised during import."""

    def __init__(self, number, validation_error, values):
        self.number = number
        self.error = validation_error
        self.error_dict = validation_error.message_dict
        self.values = values

    @property
    def field_specific_errors(self):
        """Returns a dictionary of field-specific validation errors for this row."""
        return {
            key: value for key, value in self.error_dict.items()
            if key != NON_FIELD_ERRORS
        }

    @property
    def non_field_specific_errors(self):
        """Returns a list of non field-specific validation errors for this row."""
        return self.error_dict.get(NON_FIELD_ERRORS, [])

    @property
    def error_count(self):
        """Returns the total number of validation errors for this row."""
        count = 0
        for error_list in self.error_dict.values():
            count += len(error_list)
        return count


class Result(object):
    def __init__(self, *args, **kwargs):
        super(Result, self).__init__()
        self.base_errors = []
        self.diff_headers = []
        self.rows = []  # RowResults
        self.invalid_rows = []  # InvalidRow
        self.failed_dataset = Dataset()
        self.totals = OrderedDict([(RowResult.IMPORT_TYPE_NEW, 0),
                                   (RowResult.IMPORT_TYPE_UPDATE, 0),
                                   (RowResult.IMPORT_TYPE_DELETE, 0),
                                   (RowResult.IMPORT_TYPE_SKIP, 0),
                                   (RowResult.IMPORT_TYPE_ERROR, 0),
                                   (RowResult.IMPORT_TYPE_INVALID, 0)])
        self.total_rows = 0

    def valid_rows(self):
        return [
            r for r in self.rows
            if r.import_type in RowResult.valid_import_types
        ]

    def append_row_result(self, row_result):
        self.rows.append(row_result)

    def append_base_error(self, error):
        self.base_errors.append(error)

    def add_dataset_headers(self, headers):
        self.failed_dataset.headers = headers + ["Error"]

    def append_failed_row(self, row, error):
        row_values = [v for (k, v) in row.items()]
        try:
            row_values.append(str(error.error))
        except AttributeError:
            row_values.append(str(error))
        self.failed_dataset.append(row_values)

    def append_invalid_row(self, number, row, validation_error):
        row_values = [row.get(header, '') for header in self.diff_headers]
        self.invalid_rows.append(InvalidRow(
            number=number,
            validation_error=validation_error,
            values=row_values,
        ))

    def increment_row_result_total(self, row_result):
        if row_result.import_type:
            self.totals[row_result.import_type] += 1

    def row_errors(self):
        return [(i + 1, row.errors)
                for i, row in enumerate(self.rows) if row.errors]

    def has_errors(self):
        """Returns a boolean indicating whether the import process resulted in
        any critical (non-validation) errors for this result."""
        return bool(self.base_errors or self.row_errors())

    def has_validation_errors(self):
        """Returns a boolean indicating whether the import process resulted in
        any validation errors for this result."""
        return bool(self.invalid_rows)

    def has_valid_rows(self):
        """Returns a boolean indicating whether the import process managed to
        create at least one valid result (without validation or other errors)"""
        for import_type in RowResult.valid_import_types:
            print(import_type)
            if self.totals[import_type]:
                return True

    def __iter__(self):
        return iter(self.rows)
