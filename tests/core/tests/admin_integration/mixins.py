import os

from core.admin import BookAdmin
from django.contrib.auth.models import User

from import_export.formats.base_formats import DEFAULT_FORMATS


class AdminTestMixin(object):
    category_change_url = "/admin/core/category/"
    book_import_url = "/admin/core/book/import/"
    book_process_import_url = "/admin/core/book/process_import/"
    legacybook_import_url = "/admin/core/legacybook/import/"
    legacybook_process_import_url = "/admin/core/legacybook/process_import/"
    child_import_url = "/admin/core/child/import/"
    child_process_import_url = "/admin/core/child/process_import/"

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user("admin", "admin@example.com", "password")
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save()
        self.client.login(username="admin", password="password")

    def _do_import_post(
        self, url, filename, input_format=0, encoding=None, resource=None, follow=False
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
            data = {
                "input_format": str(input_format),
                "import_file": f,
            }
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
