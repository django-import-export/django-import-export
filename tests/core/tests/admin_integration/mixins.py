import os
from datetime import datetime

from core.admin import BookAdmin
from django.contrib.auth.models import User

from import_export.formats.base_formats import DEFAULT_FORMATS


class AdminTestMixin:
    category_change_url = "/admin/core/category/"
    category_export_url = "/admin/core/category/export/"
    uuid_category_change_url = "/admin/core/uuidcategory/"
    uuid_category_export_url = "/admin/core/uuidcategory/export/"
    book_import_url = "/admin/core/book/import/"
    book_export_url = "/admin/core/book/export/"
    ebook_import_url = "/admin/core/ebook/import/"
    ebook_export_url = "/admin/core/ebook/export/"
    core_book_url = "/admin/core/book/"
    process_ebook_import_url = "/admin/core/ebook/process_import/"
    book_process_import_url = "/admin/core/book/process_import/"
    ebook_process_import_url = "/admin/core/ebook/process_import/"
    legacybook_import_url = "/admin/core/legacybook/import/"
    legacybook_process_import_url = "/admin/core/legacybook/process_import/"
    core_author_url = "/admin/core/author/"
    child_import_url = "/admin/core/child/import/"
    change_list_url = "admin/import_export/change_list.html"
    child_process_import_url = "/admin/core/child/process_import/"
    admin_import_template_url = "admin/import_export/import.html"
    change_list_template_url = "admin/import_export/change_list_import_export.html"
    import_export_import_template_url = "admin/import_export/import.html"

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user("admin", "admin@example.com", "password")
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save()
        self.client.login(username="admin", password="password")

    def _do_import_post(
        self,
        url,
        filename,
        input_format=0,
        encoding=None,
        resource=None,
        follow=False,
        data=None,
    ):
        input_format = input_format
        filename = os.path.join(
            os.path.dirname(__file__),
            os.path.pardir,
            os.path.pardir,
            "exports",
            filename,
        )
        with open(filename, "rb") as f:
            if data is None:
                data = {}
            data.update(
                {
                    "format": str(input_format),
                    "import_file": f,
                }
            )
            if encoding:
                BookAdmin.from_encoding = encoding
            if resource:
                data.update({"resource": resource})
            response = self.client.post(url, data, follow=follow)
        return response

    def _assert_string_in_response(
        self,
        url,
        filename,
        input_format,
        encoding=None,
        str_in_response=None,
        follow=False,
        status_code=200,
    ):
        response = self._do_import_post(
            url, filename, input_format, encoding=encoding, follow=follow
        )
        self.assertEqual(response.status_code, status_code)
        self.assertIn("result", response.context)
        self.assertFalse(response.context["result"].has_errors())
        if str_in_response is not None:
            self.assertContains(response, str_in_response)

    def _get_input_format_index(self, format):
        for i, f in enumerate(DEFAULT_FORMATS):
            if f().get_title() == format:
                xlsx_index = i
                break
        else:
            raise Exception(
                "Unable to find %s format. DEFAULT_FORMATS: %r"
                % (format, DEFAULT_FORMATS)
            )
        return xlsx_index

    def _check_export_file_response(
        self, response, target_file_contents, file_prefix="Book"
    ):
        date_str = datetime.now().strftime("%Y-%m-%d")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.has_header("Content-Disposition"))
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertEqual(
            response["Content-Disposition"],
            f'attachment; filename="{file_prefix}-{date_str}.csv"',
        )
        self.assertEqual(target_file_contents.encode(), response.content)

    def _get_url_response(
        self, url, expected_status_code=200, str_in_response=None, html=False
    ):
        response = self.client.get(url)
        assert response.status_code == expected_status_code
        if str_in_response is not None:
            assert str_in_response in response.content.decode()
        if html:
            assert (
                "text/html" in response.headers["Content-Type"]
            ), "Response is not HTML"
        return response

    def _post_url_response(self, url, data, expected_status_code=200, follow=False):
        response = self.client.post(url, data, follow=follow)
        assert response.status_code == expected_status_code
        return response
