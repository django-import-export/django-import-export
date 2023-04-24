import warnings
from unittest import TestCase


class ExceptionTest(TestCase):
    # exceptions.py is deprecated but this test ensures
    # there is code coverage

    def test_field_error(self):
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            from import_export import exceptions

            exceptions.FieldError()
