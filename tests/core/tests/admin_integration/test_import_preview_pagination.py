import os
from io import StringIO

from core.models import Book
from core.tests.admin_integration.mixins import AdminTestMixin
from django.core.exceptions import ImproperlyConfigured
from django.test.testcases import TestCase
from django.test.utils import override_settings

from import_export.constants import FORM_FIELD_PREFIX


def _build_csv(num_rows):
    lines = ["id,name,author_email"]
    for i in range(1, num_rows + 1):
        lines.append(f"{i},Book {i},reader{i}@example.com")
    return "\r\n".join(lines) + "\r\n"


class ImportPreviewPaginationTests(AdminTestMixin, TestCase):

    def _post_csv(self, csv_text, resource=None):
        data = {
            f"{FORM_FIELD_PREFIX}format": "0",
            "import_file": StringIO(csv_text),
        }
        if resource is not None:
            data[f"{FORM_FIELD_PREFIX}resource"] = resource
        return self.client.post(self.book_import_url, data)

    def _pagination_get_params(self, response, **page_kwargs):
        # Build the GET query params that the in-page pagination links carry.
        # Only the temporary-storage filename (a server-generated random id)
        # is round-tripped; everything else is kept server-side in the
        # session.
        confirm_form = response.context["confirm_form"]
        params = {
            "import_file_name": os.path.basename(
                confirm_form.initial["import_file_name"]
            )
        }
        params.update(page_kwargs)
        return params

    def test_default_page_size_context_is_set(self):
        response = self._post_csv(_build_csv(2))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["preview_page_size"], 100)
        page = response.context["preview_page"]
        self.assertEqual(page.paginator.count, 2)
        self.assertEqual(page.paginator.per_page, 100)
        self.assertEqual(len(page), 2)

    def test_empty_preview_renders_no_pagination(self):
        response = self._post_csv("id,name,author_email\r\n")
        # An empty file is rejected before the dry-run runs, so there is no
        # result and no preview context.
        self.assertNotIn("result", response.context)
        self.assertNotIn("preview_page", response.context)

    @override_settings(IMPORT_EXPORT_PREVIEW_PAGE_SIZE=3)
    def test_single_page_no_nav(self):
        response = self._post_csv(_build_csv(3))
        page = response.context["preview_page"]
        self.assertEqual(page.paginator.count, 3)
        self.assertEqual(page.paginator.num_pages, 1)
        self.assertEqual(len(page), 3)
        # No pagination nav rendered when there's only one page.
        body = response.content.decode()
        self.assertNotIn("page=2", body)

    @override_settings(IMPORT_EXPORT_PREVIEW_PAGE_SIZE=3)
    def test_multi_page_renders_pagination_nav(self):
        response = self._post_csv(_build_csv(5))
        page = response.context["preview_page"]
        self.assertEqual(page.paginator.count, 5)
        self.assertEqual(page.paginator.num_pages, 2)
        self.assertEqual(page.number, 1)
        self.assertEqual(len(page), 3)

        body = response.content.decode()
        # Page-of-pages indicator and a Next link to page 2 are present.
        self.assertIn("Page 1 of 2", body)
        self.assertIn("page=2", body)
        # Only the first 3 rows render on page 1.
        self.assertEqual(body.count('<td class="import-type">'), 3)

    @override_settings(IMPORT_EXPORT_PREVIEW_PAGE_SIZE=2)
    def test_custom_page_size_is_honoured(self):
        response = self._post_csv(_build_csv(5))
        self.assertEqual(response.context["preview_page_size"], 2)
        page = response.context["preview_page"]
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
        page = response.context["preview_page"]
        self.assertEqual(page.paginator.count, 5)
        self.assertEqual(len(page), 3)
        body = response.content.decode()
        self.assertIn("Page 1 of 2", body)
        self.assertIn("page=2", body)

    @override_settings(IMPORT_EXPORT_PREVIEW_PAGE_SIZE=3)
    def test_second_page_navigation_renders_remaining_rows(self):
        # The initial POST upload renders page 1; the GET pagination
        # request re-derives the dry-run from tmp_storage and renders
        # page 2 with the remaining rows.
        post_response = self._post_csv(_build_csv(5))
        params = self._pagination_get_params(post_response, page=2)

        get_response = self.client.get(self.book_import_url, params)
        self.assertEqual(get_response.status_code, 200)
        page = get_response.context["preview_page"]
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

    @override_settings(IMPORT_EXPORT_PREVIEW_PAGE_SIZE=3)
    def test_pagination_url_does_not_leak_original_filename(self):
        # `original_file_name` is treated as PII and must not be round-
        # tripped through the pagination links: the URL only carries the
        # server-generated tmp_storage name.
        response = self._post_csv(_build_csv(5))
        body = response.content.decode()
        self.assertIn("page=2", body)
        self.assertNotIn("original_file_name=", body)
        # Format and resource are also kept server-side now.
        self.assertNotIn("&format=", body)
        self.assertNotIn("&resource=", body)

    @override_settings(IMPORT_EXPORT_PREVIEW_PAGE_SIZE=3)
    def test_get_pagination_invokes_choose_import_resource_class(self):
        # Subclasses can override choose_import_resource_class to pick a
        # resource based on form state. The GET pagination handler must go
        # through the same hook on every page click; otherwise multi-
        # resource setups silently switch to the wrong resource on page 2+.
        from core.admin import BookAdmin

        calls = []
        original = BookAdmin.choose_import_resource_class

        def recording_choose(self, form, request):
            calls.append(form)
            return original(self, form, request)

        BookAdmin.choose_import_resource_class = recording_choose
        try:
            post_response = self._post_csv(_build_csv(5), resource="1")
            params = self._pagination_get_params(post_response, page=2)
            self.client.get(self.book_import_url, params)
        finally:
            BookAdmin.choose_import_resource_class = original

        # Once for the POST (the dry-run on upload) and once for the GET
        # (the page-2 navigation re-deriving the dry-run).
        self.assertEqual(len(calls), 2)
        # The form passed on the GET path carries the resource selection
        # via prefixed data, so get_resource_index keeps returning 1.
        get_form = calls[1]
        prefixed_key = f"{FORM_FIELD_PREFIX}resource"
        self.assertEqual(get_form.data.get(prefixed_key), "1")

    @override_settings(IMPORT_EXPORT_PREVIEW_PAGE_SIZE=3)
    def test_negative_page_does_not_crash(self):
        post_response = self._post_csv(_build_csv(5))
        params = self._pagination_get_params(post_response, page=-1)
        get_response = self.client.get(self.book_import_url, params)
        self.assertEqual(get_response.status_code, 200)
        # A malformed page number falls back to page 1.
        page = get_response.context["preview_page"]
        self.assertEqual(page.number, 1)

    @override_settings(IMPORT_EXPORT_PREVIEW_PAGE_SIZE=3)
    def test_non_integer_page_does_not_crash(self):
        post_response = self._post_csv(_build_csv(5))
        params = self._pagination_get_params(post_response, page="abc")
        get_response = self.client.get(self.book_import_url, params)
        self.assertEqual(get_response.status_code, 200)
        page = get_response.context["preview_page"]
        self.assertEqual(page.number, 1)

    def test_pagination_get_without_session_metadata_renders_blank(self):
        # If the session entry is missing (stale URL, expired session)
        # the GET pagination handler bails out and explains itself rather
        # than silently re-rendering an empty upload form.
        response = self.client.get(
            self.book_import_url,
            {"import_file_name": "missing.csv", "page": "2"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("result", response.context)
        self.assertIn(
            "The import preview has expired. Please upload the file again.",
            [str(m) for m in response.context["messages"]],
        )

    @override_settings(IMPORT_EXPORT_PREVIEW_PAGE_SIZE=2)
    def test_pagination_get_with_missing_tmp_file_warns(self):
        # CacheStorage entries expire, temp folders get swept, and with
        # TempFolderStorage behind a load balancer the GET can land on a
        # different host.  The admin must be told, not shown a blank form.
        post_response = self._post_csv(_build_csv(4))
        params = self._pagination_get_params(post_response, page=2)
        # the default TempFolderStorage keeps the upload on disk
        os.remove(post_response.context["confirm_form"].initial["import_file_name"])

        response = self.client.get(self.book_import_url, params)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("result", response.context)
        self.assertIn(
            "The import preview has expired. Please upload the file again.",
            [str(m) for m in response.context["messages"]],
        )

    @override_settings(IMPORT_EXPORT_PREVIEW_PAGE_SIZE=None)
    def test_pagination_can_be_disabled(self):
        # None restores the pre-v5 behaviour: every preview row on one page
        # and no navigation links.
        response = self._post_csv(_build_csv(5))
        page = response.context["preview_page"]
        self.assertEqual(page.paginator.num_pages, 1)
        self.assertEqual(page.paginator.count, 5)
        self.assertEqual(len(page), 5)
        self.assertNotContains(response, 'class="paginator"')

    @override_settings(IMPORT_EXPORT_PREVIEW_PAGE_SIZE=100)
    def test_model_admin_attribute_overrides_setting(self):
        from core.admin import BookAdmin

        BookAdmin.import_preview_page_size = 2
        try:
            response = self._post_csv(_build_csv(5))
        finally:
            BookAdmin.import_preview_page_size = None

        page = response.context["preview_page"]
        self.assertEqual(response.context["preview_page_size"], 2)
        self.assertEqual(page.paginator.num_pages, 3)

    def test_invalid_page_size_raises_improperly_configured(self):
        # A misconfigured page size used to reach Paginator and blow up
        # with ZeroDivisionError / EmptyPage / TypeError part-way through
        # rendering the confirm screen.
        for bad_value in (0, -1, "abc", True):
            with self.subTest(page_size=bad_value):
                with override_settings(IMPORT_EXPORT_PREVIEW_PAGE_SIZE=bad_value):
                    with self.assertRaises(ImproperlyConfigured):
                        self._post_csv(_build_csv(2))

    @override_settings(
        IMPORT_EXPORT_SKIP_ADMIN_CONFIRM=True, IMPORT_EXPORT_PREVIEW_PAGE_SIZE=2
    )
    def test_skip_confirm_error_preview_renders_all_rows(self):
        # With the confirm step skipped there is no tmp_storage file to
        # navigate back to, so paginating would hide rows behind links
        # that cannot work. Every row must render on a single page.
        lines = ["id,name,published"]
        for i in range(1, 6):
            lines.append(f"{i},Book {i},1996x-01-01")
        response = self._post_csv("\r\n".join(lines) + "\r\n")

        page = response.context["preview_page"]
        self.assertEqual(page.paginator.num_pages, 1)
        self.assertEqual(len(page), 5)
        body = response.content.decode()
        self.assertNotIn("page=2", body)
        self.assertEqual(body.count('<span class="validation-error-count">'), 5)

    @override_settings(IMPORT_EXPORT_PREVIEW_PAGE_SIZE=2)
    def test_confirm_from_second_page_imports_every_row(self):
        # The confirm form rendered alongside page 2 must carry the same
        # upload metadata as page 1's, so confirming from any page still
        # imports the whole file.
        post_response = self._post_csv(_build_csv(5))
        params = self._pagination_get_params(post_response, page=2)
        get_response = self.client.get(self.book_import_url, params)

        data = get_response.context["confirm_form"].initial
        self._prepend_form_prefix(data)
        process_response = self._post_url_response(
            self.book_process_import_url, data, follow=True
        )
        self.assertEqual(process_response.status_code, 200)
        self.assertEqual(Book.objects.count(), 5)

    @override_settings(IMPORT_EXPORT_PREVIEW_PAGE_SIZE=3)
    def test_custom_confirm_form_initial_survives_pagination(self):
        # Subclasses add hidden fields to ConfirmImportForm by overriding
        # get_confirm_form_initial. Those values have to be present on
        # every preview page, not just the one rendered by the POST.
        from core.admin import BookAdmin

        original = BookAdmin.get_confirm_form_initial

        def extra_initial(self, request, import_form):
            initial = original(self, request, import_form)
            initial["custom_field"] = "custom-value"
            return initial

        BookAdmin.get_confirm_form_initial = extra_initial
        try:
            post_response = self._post_csv(_build_csv(5))
            self.assertEqual(
                post_response.context["confirm_form"].initial["custom_field"],
                "custom-value",
            )
            params = self._pagination_get_params(post_response, page=2)
            get_response = self.client.get(self.book_import_url, params)
        finally:
            BookAdmin.get_confirm_form_initial = original

        self.assertEqual(
            get_response.context["confirm_form"].initial["custom_field"],
            "custom-value",
        )

    @override_settings(IMPORT_EXPORT_PREVIEW_PAGE_SIZE=3)
    def test_import_kwargs_hooks_receive_form_on_pagination_get(self):
        # get_import_resource_kwargs() / get_import_data_kwargs() are
        # documented to receive the import form. Page navigation has no
        # bound upload, so a synthetic form carrying the original
        # selections is passed instead of None.
        from core.admin import BookAdmin

        forms = {"resource": [], "data": []}
        original_res = BookAdmin.get_import_resource_kwargs
        original_data = BookAdmin.get_import_data_kwargs

        def recording_res(self, request, **kwargs):
            forms["resource"].append(kwargs.get("form"))
            return original_res(self, request, **kwargs)

        def recording_data(self, **kwargs):
            forms["data"].append(kwargs.get("form"))
            return original_data(self, **kwargs)

        BookAdmin.get_import_resource_kwargs = recording_res
        BookAdmin.get_import_data_kwargs = recording_data
        try:
            post_response = self._post_csv(_build_csv(5))
            params = self._pagination_get_params(post_response, page=2)
            self.client.get(self.book_import_url, params)
        finally:
            BookAdmin.get_import_resource_kwargs = original_res
            BookAdmin.get_import_data_kwargs = original_data

        # The last call of each is the GET pagination request.
        self.assertIsNotNone(forms["resource"][-1])
        self.assertIsNotNone(forms["data"][-1])
        prefixed_key = f"{FORM_FIELD_PREFIX}format"
        self.assertEqual(forms["data"][-1].data.get(prefixed_key), "0")

    @override_settings(IMPORT_EXPORT_PREVIEW_PAGE_SIZE=3)
    def test_pagination_url_carries_only_the_basename(self):
        # TempFolderStorage names are absolute paths; rendering them into
        # the pagination links would expose server filesystem layout. The
        # confirm form still carries the full name on every page so the
        # confirm step opens the same file.
        post_response = self._post_csv(_build_csv(5))
        post_initial = post_response.context["confirm_form"].initial
        basename = os.path.basename(post_initial["import_file_name"])
        body = post_response.content.decode()
        self.assertIn(f"?import_file_name={basename}&page=2", body)
        self.assertNotIn(f"?import_file_name={post_initial['import_file_name']}", body)

        params = self._pagination_get_params(post_response, page=2)
        get_response = self.client.get(self.book_import_url, params)
        self.assertEqual(
            get_response.context["confirm_form"].initial["import_file_name"],
            post_initial["import_file_name"],
        )

    @override_settings(IMPORT_EXPORT_PREVIEW_PAGE_SIZE=2)
    def test_custom_import_form_field_survives_pagination(self):
        # The documented custom-form pattern (docs/admin_integration.rst,
        # "Customize admin import forms") adds an ``author`` field to the
        # ImportForm and copies it to the ConfirmImportForm via
        # ``import_form.cleaned_data["author"]`` in get_confirm_form_initial().
        # ``CustomBookAdmin`` in tests/core/admin.py is that example.
        #
        # The GET pagination handler rebuilds a synthetic ImportForm carrying
        # only ``format`` and ``resource`` and never cleans it, so any extra
        # field the admin submitted is lost: the confirm form on page 2+ has
        # no author, and confirming from that page submits a required field
        # empty.  The synthetic form should be rebuilt from the full POST data
        # and cleaned so ``cleaned_data`` is available to subclass hooks.
        from core.models import Author

        author = Author.objects.create(name="Pagination Author")
        lines = ["id,name,Email of the author"]
        for i in range(1, 4):
            lines.append(f"{i},EBook {i},reader{i}@example.com")
        csv_text = "\r\n".join(lines) + "\r\n"

        post_response = self.client.post(
            self.ebook_import_url,
            {
                f"{FORM_FIELD_PREFIX}format": "0",
                "import_file": StringIO(csv_text),
                "author": author.id,
            },
        )
        self.assertEqual(post_response.status_code, 200)
        post_initial = post_response.context["confirm_form"].initial
        self.assertEqual(post_initial["author"], author.id)
        self.assertEqual(post_response.context["preview_page"].paginator.num_pages, 2)

        params = self._pagination_get_params(post_response, page=2)
        get_response = self.client.get(self.ebook_import_url, params)
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.context["preview_page"].number, 2)

        # The confirm form rendered on page 2 must carry the same author the
        # admin selected on upload, exactly as it does on page 1.
        get_initial = get_response.context["confirm_form"].initial
        self.assertEqual(get_initial.get("author"), author.id)
