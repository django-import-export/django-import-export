from unittest import mock

import tablib
from core.models import Book
from django.test import TestCase

from import_export import resources


@mock.patch("import_export.resources.Diff", spec=True)
class SkipDiffTest(TestCase):
    """
    Tests that the meta attribute 'skip_diff' means that no diff operations are called.
    'copy.deepcopy' cannot be patched at class level because it causes interferes with
    ``resources.Resource.__init__()``.
    """

    def setUp(self):
        class _BookResource(resources.ModelResource):
            class Meta:
                model = Book
                skip_diff = True

        self.resource = _BookResource()
        self.dataset = tablib.Dataset(headers=["id", "name", "birthday"])
        self.dataset.append(["", "A.A.Milne", "1882test-01-18"])

    def test_skip_diff(self, mock_diff):
        with mock.patch("import_export.resources.deepcopy") as mock_deep_copy:
            self.resource.import_data(self.dataset)
            mock_diff.return_value.compare_with.assert_not_called()
            mock_diff.return_value.as_html.assert_not_called()
            mock_deep_copy.assert_not_called()

    def test_skip_diff_for_delete_new_resource(self, mock_diff):
        class BookResource(resources.ModelResource):
            class Meta:
                model = Book
                skip_diff = True

            def for_delete(self, row, instance):
                return True

        resource = BookResource()
        with mock.patch("import_export.resources.deepcopy") as mock_deep_copy:
            resource.import_data(self.dataset)
            mock_diff.return_value.compare_with.assert_not_called()
            mock_diff.return_value.as_html.assert_not_called()
            mock_deep_copy.assert_not_called()

    def test_skip_diff_for_delete_existing_resource(self, mock_diff):
        book = Book.objects.create()

        class BookResource(resources.ModelResource):
            class Meta:
                model = Book
                skip_diff = True

            def get_or_init_instance(self, instance_loader, row):
                return book, False

            def for_delete(self, row, instance):
                return True

        resource = BookResource()

        with mock.patch("import_export.resources.deepcopy") as mock_deep_copy:
            resource.import_data(self.dataset, dry_run=True)
            mock_diff.return_value.compare_with.assert_not_called()
            mock_diff.return_value.as_html.assert_not_called()
            mock_deep_copy.assert_not_called()

    def test_skip_diff_for_delete_skip_row_not_enabled_new_object(self, mock_diff):
        class BookResource(resources.ModelResource):
            class Meta:
                model = Book
                skip_diff = False

            def for_delete(self, row, instance):
                return True

        resource = BookResource()

        with mock.patch("import_export.resources.deepcopy") as mock_deep_copy:
            resource.import_data(self.dataset, dry_run=True)
            self.assertEqual(1, mock_diff.return_value.compare_with.call_count)
            self.assertEqual(1, mock_deep_copy.call_count)

    def test_skip_row_returns_false_when_skip_diff_is_true(self, mock_diff):
        class BookResource(resources.ModelResource):
            class Meta:
                model = Book
                skip_unchanged = True
                skip_diff = True

        resource = BookResource()

        with mock.patch(
            "import_export.resources.Resource.get_import_fields"
        ) as mock_get_import_fields:
            resource.import_data(self.dataset, dry_run=True)
            self.assertEqual(3, mock_get_import_fields.call_count)


class SkipHtmlDiffTest(TestCase):
    def test_skip_html_diff(self):
        class BookResource(resources.ModelResource):
            class Meta:
                model = Book
                skip_html_diff = True

        resource = BookResource()
        self.dataset = tablib.Dataset(headers=["id", "name", "birthday"])
        self.dataset.append(["", "A.A.Milne", "1882test-01-18"])

        with mock.patch("import_export.resources.Diff.as_html") as mock_as_html:
            resource.import_data(self.dataset, dry_run=True)
            mock_as_html.assert_not_called()
