from io import StringIO

from core.models import Book
from core.tests.admin_integration.mixins import AdminTestMixin
from django.test.testcases import TestCase
from django.test.utils import override_settings

from import_export.constants import FORM_FIELD_PREFIX


def _build_csv(num_rows):
    lines = ["id,name,author_email"]
    for i in range(1, num_rows + 1):
        lines.append(f"{i},Book {i},reader{i}@example.com")
    return "\r\n".join(lines) + "\r\n"


class ImportPreviewPaginationTests(AdminTestMixin, TestCase):

    def _post_csv(self, csv_text):
        data = {
            f"{FORM_FIELD_PREFIX}format": "0",
            "import_file": StringIO(csv_text),
        }
        return self.client.post(self.book_import_url, data)

    def test_default_page_size_context_is_set(self):
        response = self._post_csv(_build_csv(2))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["preview_page_size"], 100)
        self.assertEqual(response.context["preview_total_valid_rows"], 2)
        self.assertEqual(len(response.context["preview_valid_rows"]), 2)

    def test_empty_preview_renders_no_notice(self):
        response = self._post_csv("id,name,author_email\r\n")
        # An empty file is rejected before the dry-run runs, so there is no
        # result and no preview context. Sanity-check the upstream contract
        # so a future change does not silently start producing a preview
        # page with stale totals.
        self.assertNotIn("result", response.context)
        self.assertNotIn("preview_valid_rows", response.context)

    @override_settings(IMPORT_EXPORT_PREVIEW_PAGE_SIZE=3)
    def test_single_page_no_notice(self):
        response = self._post_csv(_build_csv(3))
        self.assertEqual(response.context["preview_total_valid_rows"], 3)
        self.assertEqual(len(response.context["preview_valid_rows"]), 3)
        self.assertNotIn(
            "All rows will be processed when you confirm the import.",
            response.content.decode(),
        )

    @override_settings(IMPORT_EXPORT_PREVIEW_PAGE_SIZE=3)
    def test_last_partial_page_renders_slice_and_notice(self):
        response = self._post_csv(_build_csv(5))
        self.assertEqual(response.context["preview_total_valid_rows"], 5)
        self.assertEqual(len(response.context["preview_valid_rows"]), 3)
        # The notice carries both the page size and the true total.
        body = response.content.decode()
        self.assertIn("Showing first 3 of 5 rows", body)
        # Only 3 row <tr> elements rendered (plus the header row).
        # Each preview row carries the import-type column.
        self.assertEqual(body.count('<td class="import-type">'), 3)

    @override_settings(IMPORT_EXPORT_PREVIEW_PAGE_SIZE=2)
    def test_custom_page_size_is_honoured(self):
        response = self._post_csv(_build_csv(5))
        self.assertEqual(response.context["preview_page_size"], 2)
        self.assertEqual(len(response.context["preview_valid_rows"]), 2)
        self.assertIn("Showing first 2 of 5 rows", response.content.decode())

    @override_settings(IMPORT_EXPORT_PREVIEW_PAGE_SIZE=3)
    def test_invalid_rows_are_paginated(self):
        # An unparseable date in a DateField triggers a per-row
        # ValidationError, which lands in result.invalid_rows.
        lines = ["id,name,published"]
        for i in range(1, 6):
            lines.append(f"{i},Book {i},1996x-01-01")
        csv_text = "\r\n".join(lines) + "\r\n"

        response = self._post_csv(csv_text)
        self.assertEqual(response.context["preview_total_invalid_rows"], 5)
        self.assertEqual(len(response.context["preview_invalid_rows"]), 3)
        self.assertIn("Showing first 3 of 5 rows", response.content.decode())

    @override_settings(IMPORT_EXPORT_PREVIEW_PAGE_SIZE=2)
    def test_confirm_step_still_imports_every_row(self):
        # Pagination is presentation only: the confirm/process step must
        # write all rows from the original tmp_storage file, not just the
        # paginated slice.
        response = self._post_csv(_build_csv(5))
        confirm_form = response.context["confirm_form"]
        data = confirm_form.initial
        self._prepend_form_prefix(data)

        process_response = self._post_url_response(
            self.book_process_import_url, data, follow=True
        )
        self.assertEqual(process_response.status_code, 200)
        self.assertEqual(Book.objects.count(), 5)
