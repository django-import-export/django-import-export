import datetime
from decimal import Decimal
from unittest import mock

import tablib
from core.models import Book, Category
from django.test import TestCase, override_settings

from import_export import fields, resources, widgets
from import_export.formats import base_formats


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


class SkipRowDateTimePrecisionTest(TestCase):
    """
    Regression test for #2018.

    Re-importing unmodified, previously-persisted data whose
    DateTimeField/TimeField differs only by sub-second precision (as
    is expected after any export/import round-trip, since the default
    text formats have no sub-second precision) must be detected as
    unchanged by skip_row when skip_unchanged is enabled.
    """

    def setUp(self):
        class BookResource(resources.ModelResource):
            class Meta:
                model = Book
                skip_unchanged = True
                report_skipped = True

        self.resource = BookResource()
        self.book = Book.objects.create(
            name="Test Book",
            added=datetime.datetime(2024, 11, 19, 12, 54, 31, 838000),
        )

    def test_microsecond_only_difference_is_skipped(self):
        dataset = self.resource.export()
        # the default text format drops the microseconds on export
        self.assertEqual("2024-11-19 12:54:31", dataset.dict[0]["added"])

        result = self.resource.import_data(dataset, dry_run=True)
        self.assertEqual(1, result.totals["skip"])
        self.assertEqual(0, result.totals["update"])

    def test_xlsx_round_trip_rounding_across_second_boundary_is_skipped(self):
        """
        A native xlsx export preserves microseconds, but the spreadsheet's
        numeric storage rounds to the nearest millisecond, which can carry a
        value across a second boundary.
        """
        book = Book.objects.create(
            name="Boundary Book",
            added=datetime.datetime(2024, 11, 19, 12, 54, 31, 999900),
        )
        xlsx = base_formats.XLSX()
        dataset = self.resource.export(
            queryset=Book.objects.filter(pk=book.pk), force_native_type=True
        )
        dataset = xlsx.create_dataset(xlsx.export_data(dataset))
        self.assertEqual(
            datetime.datetime(2024, 11, 19, 12, 54, 32), dataset.dict[0]["added"]
        )

        result = self.resource.import_data(dataset, dry_run=True)
        self.assertEqual(1, result.totals["skip"])
        self.assertEqual(0, result.totals["update"])

    def test_genuine_second_level_difference_is_not_skipped(self):
        dataset = self.resource.export()
        row = dataset.dict[0]
        row["added"] = "2024-11-19 12:54:41"  # genuinely 10 seconds later
        dataset = tablib.Dataset(headers=dataset.headers)
        dataset.append([row[h] for h in dataset.headers])

        result = self.resource.import_data(dataset, dry_run=True)
        self.assertEqual(0, result.totals["skip"])
        self.assertEqual(1, result.totals["update"])

    @override_settings(USE_TZ=True, TIME_ZONE="Europe/Ljubljana")
    def test_cross_timezone_round_trip_is_skipped(self):
        """
        The reporter of #2018 saw values in different timezones
        (``12:54:31.838000+01:00`` vs ``11:54:31.837623+00:00``) and suspected
        a timezone mismatch. Aware datetimes compare by instant, so a value
        persisted in UTC and exported / re-imported in a different local
        timezone must still be detected as unchanged.
        """
        book = Book.objects.create(
            name="Aware Book",
            added=datetime.datetime(
                2024, 11, 19, 11, 54, 31, 837623, tzinfo=datetime.timezone.utc
            ),
        )
        dataset = self.resource.export(queryset=Book.objects.filter(pk=book.pk))
        # exported in local time (UTC+1) with no sub-second precision
        self.assertEqual("2024-11-19 12:54:31", dataset.dict[0]["added"])

        result = self.resource.import_data(dataset, dry_run=True)
        self.assertEqual(1, result.totals["skip"])
        self.assertEqual(0, result.totals["update"])


class DiffEquivalentValuesTest(TestCase):
    """
    Regression test for #1425.

    The import preview diff compares the rendered (string) representation of
    the persisted value against that of the imported value.  Values which the
    widget considers equal but which render differently (for example
    ``Decimal("1803.60")`` persisted vs ``Decimal("1803.6")`` read from an xlsx
    cell) must not be shown as a change.
    """

    def setUp(self):
        class BookResource(resources.ModelResource):
            class Meta:
                model = Book
                fields = ("id", "name", "price", "added")

        self.resource = BookResource()
        self.book = Book.objects.create(
            name="Test Book",
            price=Decimal("1803.60"),
            added=datetime.datetime(2024, 11, 19, 12, 54, 31, 838000),
        )
        self.price_idx = self.resource.get_diff_headers().index("price")
        self.added_idx = self.resource.get_diff_headers().index("added")

    def _import(self, price, added="2024-11-19 12:54:31"):
        dataset = tablib.Dataset(headers=["id", "name", "price", "added"])
        dataset.append([self.book.id, "Test Book", price, added])
        result = self.resource.import_data(dataset, dry_run=True)
        self.assertEqual(1, result.totals["update"])
        return result.rows[0].diff

    def test_decimal_with_fewer_trailing_zeros_is_not_shown_as_change(self):
        # openpyxl reads a numeric cell holding 1803.60 as the float 1803.6
        diff = self._import(1803.6)
        self.assertEqual("<span>1803.60</span>", diff[self.price_idx])

    def test_decimal_string_with_fewer_trailing_zeros_is_not_shown_as_change(self):
        diff = self._import("1803.6")
        self.assertEqual("<span>1803.60</span>", diff[self.price_idx])

    def test_decimal_genuine_change_is_shown(self):
        diff = self._import("1803.70")
        self.assertIn("<del", diff[self.price_idx])
        self.assertIn("<ins", diff[self.price_idx])

    def test_decimal_change_to_empty_is_shown(self):
        diff = self._import("")
        self.assertIn("<del", diff[self.price_idx])

    def test_datetime_sub_second_difference_is_not_shown_as_change(self):
        # the default text format drops microseconds, so a re-imported export
        # differs from the persisted value only by its microseconds
        diff = self._import("1803.60")
        self.assertEqual("<span>2024-11-19 12:54:31</span>", diff[self.added_idx])

    def test_new_row_is_not_affected(self):
        dataset = tablib.Dataset(headers=["id", "name", "price", "added"])
        dataset.append(["", "New Book", 1803.6, "2024-11-19 12:54:31"])
        result = self.resource.import_data(dataset, dry_run=True)
        self.assertEqual(1, result.totals["new"])
        self.assertEqual(
            '<ins style="background:#e6ffe6;">1803.6</ins>',
            result.rows[0].diff[self.price_idx],
        )


class DiffEquivalentValuesEdgeCaseTest(TestCase):
    """
    The widget equality check added for #1425 must not change the diff for
    new rows, for many-to-many fields, or when a widget's ``is_equal`` fails.
    """

    def setUp(self):
        # explicit ids with a shared leading digit, as seen on MySQL / Postgres
        # where sequences are not reset between tests, so that the diff
        # markup is the same on every database
        self.category1 = Category.objects.create(id=41, name="Fiction")
        self.category2 = Category.objects.create(id=42, name="History")
        self.book = Book.objects.create(name="Test Book", price=Decimal("1803.60"))
        self.book.categories.set([self.category1])

    def _import(self, resource, row, dry_run=True):
        dataset = tablib.Dataset(headers=list(row.keys()))
        dataset.append(list(row.values()))
        return resource.import_data(dataset, dry_run=dry_run)

    def test_new_row_shows_imported_value_even_if_widget_says_equal(self):
        class AlwaysEqualWidget(widgets.CharWidget):
            def is_equal(self, instance_value, original_value, **kwargs):
                return True

        class BookResource(resources.ModelResource):
            name = fields.Field(attribute="name", widget=AlwaysEqualWidget())

            class Meta:
                model = Book
                fields = ("id", "name")

        resource = BookResource()
        # an unsaved Book has name "" (CharField default), which the widget
        # would deem equal to the imported name
        result = self._import(resource, {"id": "", "name": "New Book"})
        self.assertEqual(1, result.totals["new"])
        name_idx = resource.get_diff_headers().index("name")
        self.assertEqual(
            '<ins style="background:#e6ffe6;">New Book</ins>',
            result.rows[0].diff[name_idx],
        )

    def test_many_to_many_change_is_still_shown(self):
        class BookResource(resources.ModelResource):
            class Meta:
                model = Book
                fields = ("id", "name", "categories")

        resource = BookResource()
        result = self._import(
            resource,
            {"id": self.book.id, "name": "Test Book", "categories": self.category2.id},
            dry_run=False,
        )
        self.assertEqual(1, result.totals["update"])
        idx = resource.get_diff_headers().index("categories")
        self.assertEqual(
            "<span>4</span>"
            '<del style="background:#ffe6e6;">1</del>'
            '<ins style="background:#e6ffe6;">2</ins>',
            result.rows[0].diff[idx],
        )

    def test_many_to_many_unchanged_is_not_shown_as_change(self):
        class BookResource(resources.ModelResource):
            class Meta:
                model = Book
                fields = ("id", "name", "categories")

        resource = BookResource()
        result = self._import(
            resource,
            {"id": self.book.id, "name": "Test Book", "categories": self.category1.id},
            dry_run=False,
        )
        self.assertEqual(1, result.totals["update"])
        idx = resource.get_diff_headers().index("categories")
        self.assertEqual(f"<span>{self.category1.id}</span>", result.rows[0].diff[idx])

    def test_widget_is_equal_error_falls_back_to_rendered_comparison(self):
        class BrokenWidget(widgets.DecimalWidget):
            def is_equal(self, instance_value, original_value, **kwargs):
                raise ValueError("boom")

        class BookResource(resources.ModelResource):
            price = fields.Field(attribute="price", widget=BrokenWidget())

            class Meta:
                model = Book
                fields = ("id", "name", "price")

        resource = BookResource()
        result = self._import(
            resource, {"id": self.book.id, "name": "Test Book", "price": "1803.6"}
        )
        self.assertFalse(result.has_errors())
        self.assertEqual(1, result.totals["update"])
        idx = resource.get_diff_headers().index("price")
        self.assertEqual(
            '<span>1803.6</span><del style="background:#ffe6e6;">0</del>',
            result.rows[0].diff[idx],
        )

    def test_widget_is_equal_receives_row(self):
        calls = []

        class RecordingWidget(widgets.DecimalWidget):
            def is_equal(self, instance_value, original_value, **kwargs):
                calls.append(kwargs.get("row"))
                return super().is_equal(instance_value, original_value, **kwargs)

        class BookResource(resources.ModelResource):
            price = fields.Field(attribute="price", widget=RecordingWidget())

            class Meta:
                model = Book
                fields = ("id", "name", "price")

        row = {"id": self.book.id, "name": "Test Book", "price": "1803.6"}
        self._import(BookResource(), row)
        self.assertEqual(1, len(calls))
        self.assertEqual("1803.6", calls[0]["price"])


class SkipRowDateFieldTest(TestCase):
    """
    Regression test for #2195.
    """

    def setUp(self):
        class BookResource(resources.ModelResource):
            class Meta:
                model = Book
                skip_unchanged = True
                report_skipped = True

        self.resource = BookResource()

    def test_xlsx_round_trip_date_field_is_skipped(self):
        """
        An xlsx round-trip of a DateField returns a datetime instance from
        openpyxl, which DateWidget must clean to a date so that skip_row
        detects the row as unchanged.
        """
        book = Book.objects.create(
            name="Date Book",
            published=datetime.date(2024, 11, 19),
        )
        xlsx = base_formats.XLSX()
        dataset = self.resource.export(
            queryset=Book.objects.filter(pk=book.pk), force_native_type=True
        )
        dataset = xlsx.create_dataset(xlsx.export_data(dataset))
        # openpyxl produces a datetime or date instance depending on the cell type
        self.assertIsInstance(dataset.dict[0]["published"], datetime.date)

        result = self.resource.import_data(dataset, dry_run=True)
        self.assertEqual(1, result.totals["skip"])
        self.assertEqual(0, result.totals["update"])
