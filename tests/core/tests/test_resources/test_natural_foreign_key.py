import tablib
from core.models import Author, Book
from django.test import TestCase

from import_export import fields, resources, widgets


class BookUsingNaturalKeys(resources.ModelResource):
    class Meta:
        model = Book
        fields = ["name", "author"]
        use_natural_foreign_keys = True


class BookUsingAuthorNaturalKey(resources.ModelResource):
    class Meta:
        model = Book
        fields = ["name", "author"]

    author = fields.Field(
        attribute="author",
        column_name="author",
        widget=widgets.ForeignKeyWidget(
            Author,
            use_natural_foreign_keys=True,
        ),
    )


class TestNaturalKeys(TestCase):
    """Tests for issue 1816."""

    def setUp(self) -> None:
        author = Author.objects.create(name="J. R. R. Tolkien")
        Book.objects.create(author=author, name="The Hobbit")
        self.expected_dataset = tablib.Dataset(headers=["name", "author"])
        row = ["The Hobbit", '["J. R. R. Tolkien"]']
        self.expected_dataset.append(row)

    def test_resource_use_natural_keys(self):
        """
        test with ModelResource.Meta.use_natural_foreign_keys=True
        Reproduces this problem
        """
        resource = BookUsingNaturalKeys()
        exported_dataset = resource.export(Book.objects.all())
        self.assertDatasetEqual(self.expected_dataset, exported_dataset)

    def test_field_use_natural_keys(self):
        """
        test with ModelResource.field.widget.use_natural_foreign_keys=True
        Example of correct behaviour
        """
        resource = BookUsingAuthorNaturalKey()
        exported_dataset = resource.export(Book.objects.all())
        self.assertDatasetEqual(self.expected_dataset, exported_dataset)

    def assertDatasetEqual(self, expected_dataset, actual_dataset, message=None):
        """
        Util for comparing datasets
        """
        self.assertEqual(len(expected_dataset), len(actual_dataset), message)
        for expected_row, actual_row in zip(expected_dataset, actual_dataset):
            self.assertEqual(expected_row, actual_row, message)
