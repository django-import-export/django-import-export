from __future__ import unicode_literals

from django.core.exceptions import ValidationError
from django.test import TestCase

from import_export.results import InvalidRow


class InvalidRowTest(TestCase):

    def setUp(self):
        # Create a ValidationEror with a mix of field-specific and non-field-specific errors
        e = ValidationError('Error one')
        e.update_error_dict({
            'name': ['Error two', 'Error three'],
            'birthday': ['Error four', 'Error five'],
        })
        # Use the error to create an InvalidRow instance
        values = {'name': 'ABC', 'birthday': '123'}
        self.obj = InvalidRow(number=1, validation_error=e, values=values)

    def test_error_count(self):
        self.assertEqual(self.obj.error_count(), 5)

    def test_non_field_specific_errors(self):
        self.assertIsInstance(self.obj.non_field_specific_errors, list)
        self.assertEqual(len(self.obj.non_field_specific_errors), 1)
        self.assertEqual(self.obj.non_field_specific_errors[0], 'Error one')

    def test_field_specific_errors(self):
        self.assertIsInstance(self.obj.field_specific_errors, dict)
        self.assertEqual(len(self.obj.field_specific_errors), 2)
        self.assertEqual(
            self.obj.field_specific_errors['name'],
            ['Error two', 'Error three']
        )
        self.assertEqual(
            self.obj.field_specific_errors['birthday'],
            ['Error four', 'Error five']
        )
