from __future__ import unicode_literals

from django.core.exceptions import ValidationError
from django.test import TestCase

from import_export.results import InvalidRow


class InvalidRowTest(TestCase):

    def setUp(self):
        # Create a ValidationEror with a mix of field-specific and non-field-specific errors
        non_field_errors = ValidationError(['Error 1', 'Error 2', 'Error 3'])
        field_errors = ValidationError({
            'name': ['Error 4', 'Error 5'],
            'birthday': ['Error 6', 'Error 7'],
        })
        combined_error_dict = non_field_errors.update_error_dict(field_errors.error_dict)
        e = ValidationError(combined_error_dict)
        # Use the error to create an InvalidRow instance
        values = {'name': 'ABC', 'birthday': '123'}
        self.obj = InvalidRow(number=1, validation_error=e, values=values)

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
