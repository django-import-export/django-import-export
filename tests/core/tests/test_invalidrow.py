from django.core.exceptions import NON_FIELD_ERRORS, ValidationError
from django.test import TestCase

from import_export.results import InvalidRow


class InvalidRowTest(TestCase):

    def setUp(self):
        # Create a ValidationError with a mix of field-specific and non-field-specific errors
        self.non_field_errors = ValidationError(['Error 1', 'Error 2', 'Error 3'])
        self.field_errors = ValidationError({
            'name': ['Error 4', 'Error 5'],
            'birthday': ['Error 6', 'Error 7'],
        })
        combined_error_dict = self.non_field_errors.update_error_dict(
            self.field_errors.error_dict.copy()
        )
        e = ValidationError(combined_error_dict)
        # Create an InvalidRow instance to use in tests
        self.obj = InvalidRow(
            number=1,
            validation_error=e,
            values=['ABC', '123']
        )

    def test_error_count(self):
        self.assertEqual(self.obj.error_count, 7)

    def test_non_field_specific_errors(self):
        result = self.obj.non_field_specific_errors
        self.assertIsInstance(result, list)
        self.assertEqual(result, ['Error 1', 'Error 2', 'Error 3'])

    def test_field_specific_errors(self):
        result = self.obj.field_specific_errors
        self.assertIsInstance(result, dict)
        self.assertEqual(len(result), 2)
        self.assertEqual(result['name'], ['Error 4', 'Error 5'])
        self.assertEqual(result['birthday'], ['Error 6', 'Error 7'])

    def test_creates_error_dict_from_error_list_if_validation_error_only_has_error_list(self):
        obj = InvalidRow(
            number=1,
            validation_error=self.non_field_errors,
            values=[]
        )
        self.assertIsInstance(obj.error_dict, dict)
        self.assertIn(NON_FIELD_ERRORS, obj.error_dict)
        self.assertEqual(obj.error_dict[NON_FIELD_ERRORS], ['Error 1', 'Error 2', 'Error 3'])
