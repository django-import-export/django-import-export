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

    def _pagination_get_params(self, response, **page_kwargs):
        # Build the GET query params that the in-page pagination links
        # carry: file-identifying fields from the confirm_form initial,
        # plus the requested *_page numbers.
        confirm_form = response.context["confirm_form"]
        params = {
            "import_file_name": confirm_form.initial["import_file_name"],
            "original_file_name": confirm_form.initial["original_file_name"],
            "format": confirm_form.initial["format"],
            "resource": confirm_form.initial.get("resource", ""),
        }
        params.update(page_kwargs)
        return params

    def test_default_page_size_context_is_set(self):
        response = self._post_csv(_build_csv(2))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["preview_page_size"], 100)
        page = response.context["preview_valid_page"]
        self.assertEqual(page.paginator.count, 2)
        self.assertEqual(page.paginator.per_page, 100)
        self.assertEqual(len(page), 2)

    def test_empty_preview_renders_no_pagination(self):
        response = self._post_csv("id,name,author_email\r\n")
        # An empty file is rejected before the dry-run runs, so there is no
        # result and no preview context.
        self.assertNotIn("result", response.context)
        self.assertNotIn("preview_valid_page", response.context)

    @override_settings(IMPORT_EXPORT_PREVIEW_PAGE_SIZE=3)
    def test_single_page_no_nav(self):
        response = self._post_csv(_build_csv(3))
        page = response.context["preview_valid_page"]
        self.assertEqual(page.paginator.count, 3)
        self.assertEqual(page.paginator.num_pages, 1)
        self.assertEqual(len(page), 3)
        # No pagination nav rendered when there's only one page.
        body = response.content.decode()
        self.assertNotIn("valid_page=2", body)

    @override_settings(IMPORT_EXPORT_PREVIEW_PAGE_SIZE=3)
    def test_multi_page_renders_pagination_nav(self):
        response = self._post_csv(_build_csv(5))
        page = response.context["preview_valid_page"]
        self.assertEqual(page.paginator.count, 5)
        self.assertEqual(page.paginator.num_pages, 2)
        self.assertEqual(page.number, 1)
        self.assertEqual(len(page), 3)

        body = response.content.decode()
        # Page-of-pages indicator and a Next link to page 2 are present.
        self.assertIn("Page 1 of 2", body)
        self.assertIn("valid_page=2", body)
        # Only the first 3 rows render on page 1.
        self.assertEqual(body.count('<td class="import-type">'), 3)

    @override_settings(IMPORT_EXPORT_PREVIEW_PAGE_SIZE=2)
    def test_custom_page_size_is_honoured(self):
        response = self._post_csv(_build_csv(5))
        self.assertEqual(response.context["preview_page_size"], 2)
        page = response.context["preview_valid_page"]
        self.assertEqual(page.paginator.per_page, 2)
        self.assertEqual(page.paginator.num_pages, 3)
        self.assertEqual(len(page), 2)

    @override_settings(IMPORT_EXPORT_PREVIEW_PAGE_SIZE=3)
    def test_invalid_rows_are_paginated(self):
        # An unparseable date in a DateField triggers a per-row
        # ValidationError, which lands in result.invalid_rows.
        lines = ["id,name,published"]
        for i in range(1, 6):
            lines.append(f"{i},Book {i},1996x-01-01")
        csv_text = "\r\n".join(lines) + "\r\n"

        response = self._post_csv(csv_text)
        page = response.context["preview_invalid_page"]
        self.assertEqual(page.paginator.count, 5)
        self.assertEqual(len(page), 3)
        body = response.content.decode()
        self.assertIn("Page 1 of 2", body)
        self.assertIn("invalid_page=2", body)

    @override_settings(IMPORT_EXPORT_PREVIEW_PAGE_SIZE=3)
    def test_second_page_navigation_renders_remaining_rows(self):
        # The initial POST upload renders page 1; the GET pagination
        # request re-derives the dry-run from tmp_storage and renders
        # page 2 with the remaining rows.
        post_response = self._post_csv(_build_csv(5))
        params = self._pagination_get_params(post_response, valid_page=2)

        get_response = self.client.get(self.book_import_url, params)
        self.assertEqual(get_response.status_code, 200)
        page = get_response.context["preview_valid_page"]
        self.assertEqual(page.number, 2)
        self.assertEqual(page.paginator.count, 5)
        self.assertEqual(len(page), 2)

        body = get_response.content.decode()
        self.assertIn("Page 2 of 2", body)
        # Page 2 contains the last two rows.
        self.assertIn("Book 4", body)
        self.assertIn("Book 5", body)
        self.assertNotIn("Book 1", body)

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
