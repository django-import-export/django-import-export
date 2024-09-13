import os
from io import StringIO
from unittest import mock

from core.admin import BookAdmin, CustomBookAdmin
from core.models import Author, Book, EBook
from core.tests.admin_integration.mixins import AdminTestMixin
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.test import RequestFactory
from django.test.testcases import TestCase
from django.test.utils import override_settings
from django.utils.translation import gettext_lazy as _

from import_export.exceptions import FieldError


class ImportErrorHandlingTests(AdminTestMixin, TestCase):

    def test_import_action_handles_UnicodeDecodeError_as_form_error(self):
        with mock.patch(
            "import_export.admin.TempFolderStorage.read"
        ) as mock_tmp_folder_storage:
            b_arr = b"\x00"
            mock_tmp_folder_storage.side_effect = UnicodeDecodeError(
                "codec", b_arr, 1, 2, "fail!"
            )
            response = self._do_import_post(self.book_import_url, "books.csv")
        self.assertEqual(response.status_code, 200)
        target_msg = (
            "'UnicodeDecodeError' encountered while trying to read file. "
            "Ensure you have chosen the correct format for the file."
        )
        self.assertFormError(response.context["form"], "import_file", target_msg)

    def test_import_action_handles_ValueError_as_form_error(self):
        with mock.patch(
            "import_export.admin.TempFolderStorage.read"
        ) as mock_tmp_folder_storage:
            mock_tmp_folder_storage.side_effect = ValueError("some unknown error")
            response = self._do_import_post(self.book_import_url, "books.csv")
        self.assertEqual(response.status_code, 200)
        target_msg = (
            "'ValueError' encountered while trying to read file. "
            "Ensure you have chosen the correct format for the file."
        )
        self.assertFormError(response.context["form"], "import_file", target_msg)

    def test_import_action_handles_FieldError(self):
        # issue 1722
        with mock.patch(
            "import_export.resources.Resource._check_import_id_fields"
        ) as mock_check_import_id_fields:
            mock_check_import_id_fields.side_effect = FieldError("some unknown error")
            response = self._do_import_post(self.book_import_url, "books.csv")
        self.assertEqual(response.status_code, 200)
        target_msg = "some unknown error"
        self.assertIn(target_msg, response.content.decode())

    @override_settings(LANGUAGE_CODE="es")
    def test_import_action_handles_ValueError_as_form_error_with_translation(self):
        with mock.patch(
            "import_export.admin.TempFolderStorage.read"
        ) as mock_tmp_folder_storage:
            mock_tmp_folder_storage.side_effect = ValueError("some unknown error")
            response = self._do_import_post(self.book_import_url, "books.csv")
        self.assertEqual(response.status_code, 200)
        target_msg = (
            "Se encontró 'ValueError' mientras se intentaba leer el archivo. "
            "Asegúrese que seleccionó el formato correcto para el archivo."
        )
        self.assertFormError(response.context["form"], "import_file", target_msg)

    def test_import_with_customized_form_handles_form_validation(self):
        """Test if admin import handles errors gracefully when confirm_form is
        invalid for eg. if a required field (in this case 'Author') is left blank.
        """
        # We use customized BookAdmin (CustomBookAdmin) with modified import
        # form, which requires Author to be selected (from available authors).
        # Note that url is /admin/core/ebook/import (and not: ...book/import)!

        # We need a author in the db to select from in the admin import custom
        # forms, first we will submit data with invalid author_id and if the
        # error is handled correctly, resubmit form with correct author_id and
        # check if data is imported successfully
        Author.objects.create(id=11, name="Test Author")

        # GET the import form
        response = self._get_url_response(
            self.ebook_import_url, str_in_response='form action=""'
        )
        self.assertTemplateUsed(response, self.admin_import_template_url)
        # POST the import form
        input_format = "0"
        filename = os.path.join(
            os.path.dirname(__file__),
            os.path.pardir,
            os.path.pardir,
            "exports",
            "books.csv",
        )
        with open(filename, "rb") as fobj:
            data = {"author": 11, "format": input_format, "import_file": fobj}
            response = self._post_url_response(self.ebook_import_url, data)

        self.assertIn("result", response.context)
        self.assertFalse(response.context["result"].has_errors())
        self.assertIn("confirm_form", response.context)
        confirm_form = response.context["confirm_form"]
        self.assertIsInstance(
            confirm_form,
            CustomBookAdmin(EBook, "ebook/import").get_confirm_form_class(None),
        )

        data = confirm_form.initial
        self.assertEqual(data["original_file_name"], "books.csv")

        # manipulate data to make the payload invalid
        data["author"] = ""
        response = self._post_url_response(
            self.ebook_process_import_url, data, follow=True
        )

        # check if error is captured gracefully
        self.assertEqual(
            response.context["errors"], {"author": ["This field is required."]}
        )

        # resubmit with valid data
        data["author"] = 11
        response = self._post_url_response(
            self.ebook_process_import_url, data, follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            _(
                "Import finished: {} new, {} updated, {} deleted and {} skipped {}."
            ).format(1, 0, 0, 0, EBook._meta.verbose_name_plural),
        )

    def test_import_action_invalid_date(self):
        # test that a row with an invalid date redirects to errors page
        index = self._get_input_format_index("csv")
        response = self._do_import_post(
            self.book_import_url, "books-invalid-date.csv", index
        )
        result = response.context["result"]
        # there should be a single invalid row
        self.assertEqual(1, len(result.invalid_rows))
        self.assertEqual(
            "Value could not be parsed using defined formats.",
            result.invalid_rows[0].error.messages[0],
        )
        # no rows should be imported because we rollback on validation errors
        self.assertEqual(0, Book.objects.count())

    def test_import_action_error_on_save(self):
        with mock.patch("core.models.Book.save") as mock_save:
            mock_save.side_effect = ValueError("some unknown error")
            response = self._do_import_post(self.book_import_url, "books.csv")
        self.assertIn("some unknown error", response.content.decode())

    def test_import_action_invalidates_data_sheet_with_no_headers_or_data(self):
        # GET the import form
        response = self._get_url_response(
            self.book_import_url, str_in_response='form action=""'
        )
        self.assertTemplateUsed(response, self.admin_import_template_url)

        response = self._do_import_post(
            self.book_import_url, "books-no-headers.csv", input_format=0
        )
        self.assertEqual(response.status_code, 200)
        target_msg = (
            "No valid data to import. Ensure your file "
            "has the correct headers or data for import."
        )
        self.assertFormError(response.context["form"], "import_file", target_msg)


class TestImportErrorMessageFormat(AdminTestMixin, TestCase):
    # issue 1724

    def setUp(self):
        super().setUp()
        self.csvdata = "id,name,author\r\n" "1,Ulysses,666\r\n"
        self.filedata = StringIO(self.csvdata)
        self.data = {"format": "0", "import_file": self.filedata}
        self.model_admin = BookAdmin(Book, AdminSite())

        factory = RequestFactory()
        self.request = factory.post(self.book_import_url, self.data, follow=True)
        self.request.user = User.objects.create_user("admin1")

    def test_result_error_display_default(self):
        response = self.model_admin.import_action(self.request)
        response.render()
        content = response.content.decode()
        self.assertIn("import-error-display-message", content)
        self.assertIn(
            "Line number: 1 - Author matching query does not exist.",
            content,
        )
        self.assertNotIn("import-error-display-row", content)
        self.assertNotIn("import-error-display-traceback", content)

    def test_result_error_display_message_only(self):
        self.model_admin.import_error_display = ("message",)

        response = self.model_admin.import_action(self.request)
        response.render()
        content = response.content.decode()
        self.assertIn(
            "Line number: 1 - Author matching query does not exist.",
            content,
        )
        self.assertIn("import-error-display-message", content)
        self.assertNotIn("import-error-display-row", content)
        self.assertNotIn("import-error-display-traceback", content)

    def test_result_error_display_row_only(self):
        self.model_admin.import_error_display = ("row",)

        response = self.model_admin.import_action(self.request)
        response.render()
        content = response.content.decode()
        self.assertNotIn(
            "Line number: 1 - Author matching query does not exist.",
            content,
        )
        self.assertNotIn("import-error-display-message", content)
        self.assertIn("import-error-display-row", content)
        self.assertNotIn("import-error-display-traceback", content)

    def test_result_error_display_traceback_only(self):
        self.model_admin.import_error_display = ("traceback",)

        response = self.model_admin.import_action(self.request)
        response.render()
        content = response.content.decode()
        self.assertNotIn(
            "Line number: 1 - Author matching query does not exist.",
            content,
        )
        self.assertNotIn("import-error-display-message", content)
        self.assertNotIn("import-error-display-row", content)
        self.assertIn("import-error-display-traceback", content)
        self.assertIn("Traceback (most recent call last)", content)
