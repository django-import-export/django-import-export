from unittest import mock
from unittest.mock import PropertyMock, patch

from core.admin import BookAdmin, EBookResource, ImportMixin
from core.models import Author, Book, Parent
from core.tests.admin_integration.mixins import AdminTestMixin
from django.contrib.admin.models import DELETION, LogEntry
from django.core.exceptions import ValidationError
from django.test.testcases import TestCase, TransactionTestCase
from django.test.utils import override_settings
from django.utils.translation import gettext_lazy as _

from import_export.admin import ExportMixin
from import_export.formats import base_formats
from import_export.resources import ModelResource


class ImportAdminIntegrationTest(AdminTestMixin, TestCase):

    @patch(
        "core.admin.BookAdmin.skip_import_confirm",
        new_callable=PropertyMock,
        return_value=True,
    )
    def test_import_skips_confirm_page(self, mock_skip_import_confirm):
        response = self._do_import_post(self.book_import_url, "books.csv", follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            _(
                "Import finished: {} new, {} updated, {} deleted and {} skipped {}."
            ).format(1, 0, 0, 0, Book._meta.verbose_name_plural),
        )

    def test_delete_from_admin(self):
        # test delete from admin site (see #432)

        # create a book which can be deleted
        b = Book.objects.create(id=1)

        response = self._do_import_post(self.book_import_url, "books-for-delete.csv")
        self.assertEqual(response.status_code, 200)
        confirm_form = response.context["confirm_form"]
        data = confirm_form.initial
        self._post_url_response(self.book_process_import_url, data, follow=True)

        # check the LogEntry was created as expected
        deleted_entry = LogEntry.objects.latest("id")
        self.assertEqual("delete through import_export", deleted_entry.change_message)
        self.assertEqual(DELETION, deleted_entry.action_flag)
        self.assertEqual(b.id, int(deleted_entry.object_id))
        self.assertEqual("", deleted_entry.object_repr)

    @override_settings(TEMPLATE_STRING_IF_INVALID="INVALID_VARIABLE")
    @patch("import_export.admin.ImportMixin.choose_import_resource_class")
    def test_import_passes_correct_kwargs_to_constructor(
        self, mock_choose_import_resource_class
    ):
        # issue 1741
        class TestResource(ModelResource):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)

                # the form is passed as a kwarg to the Resource constructor
                # if not present, then it means that the original kwargs were lost
                if "form" not in kwargs:
                    raise Exception("No form")

            class Meta:
                model = Book
                fields = ("id",)

        # mock the returned resource class so that we can inspect constructor params
        mock_choose_import_resource_class.return_value = TestResource

        response = self._do_import_post(self.book_import_url, "books.csv")
        self.assertEqual(response.status_code, 200)

    def test_get_tmp_storage_class_attribute(self):
        """Mock dynamically loading a class defined by an attribute"""
        target = "SomeClass"
        m = ImportMixin()
        m.tmp_storage_class = "tmpClass"
        with mock.patch("import_export.admin.import_string") as mock_import_string:
            mock_import_string.return_value = target
            self.assertEqual(target, m.get_tmp_storage_class())

    def test_get_import_data_kwargs_with_form_kwarg(self):
        """
        Test that if the method is called with a 'form' kwarg,
        then it is removed and the updated dict is returned
        """
        m = ImportMixin()
        kw = {"a": 1, "form": "some_form"}
        target = {"a": 1}
        self.assertEqual(target, m.get_import_data_kwargs(**kw))

    def test_get_import_data_kwargs_with_no_form_kwarg_returns_kwarg_dict(self):
        """
        Test that if the method is called with no 'form' kwarg,
        then an empty dict is returned
        """
        m = ImportMixin()
        kw = {
            "a": 1,
        }
        target = {"a": 1}
        self.assertEqual(target, m.get_import_data_kwargs(**kw))

    def test_get_context_data_returns_empty_dict(self):
        m = ExportMixin()
        self.assertEqual({}, m.get_context_data())

    @override_settings(IMPORT_FORMATS=[base_formats.XLSX, base_formats.XLS])
    def test_import_admin_uses_import_format_settings(self):
        """
        Test that import form only avails the formats provided by the
        IMPORT_FORMATS setting
        """
        request = self._get_url_response(self.book_import_url).wsgi_request
        mock_site = mock.MagicMock()
        import_form = BookAdmin(Book, mock_site).create_import_form(request)

        file_format = import_form.fields["format"]
        choices = file_format.choices

        self.assertEqual(len(choices), 3)
        self.assertEqual(choices[0][1], "---")
        self.assertEqual(choices[1][1], "xlsx")
        self.assertEqual(choices[2][1], "xls")

    @override_settings(IMPORT_FORMATS=[])
    def test_export_empty_import_formats(self):
        with self.assertRaisesRegex(ValueError, "invalid formats list"):
            self._get_url_response(self.book_import_url)


class ImportFileHandlingTests(AdminTestMixin, TestCase):

    @override_settings(TEMPLATE_STRING_IF_INVALID="INVALID_VARIABLE")
    def test_import(self):
        # GET the import form
        response = self._get_url_response(
            self.book_import_url, str_in_response='form action=""'
        )
        self.assertTemplateUsed(response, self.admin_import_template_url)

        response = self._do_import_post(self.book_import_url, "books.csv")
        self.assertIn("result", response.context)
        self.assertFalse(response.context["result"].has_errors())
        self.assertIn("confirm_form", response.context)
        confirm_form = response.context["confirm_form"]

        data = confirm_form.initial
        self.assertEqual(data["original_file_name"], "books.csv")
        response = self._post_url_response(
            self.book_process_import_url, data, follow=True
        )
        self.assertContains(
            response,
            _(
                "Import finished: {} new, {} updated, {} deleted and {} skipped {}."
            ).format(1, 0, 0, 0, Book._meta.verbose_name_plural),
        )

    def test_import_mac(self):
        # GET the import form
        response = self._get_url_response(
            self.book_import_url, str_in_response='form action=""'
        )
        self.assertTemplateUsed(response, self.admin_import_template_url)

        response = self._do_import_post(self.book_import_url, "books-mac.csv")
        self.assertIn("result", response.context)
        self.assertFalse(response.context["result"].has_errors())
        self.assertIn("confirm_form", response.context)
        confirm_form = response.context["confirm_form"]

        data = confirm_form.initial
        self.assertEqual(data["original_file_name"], "books-mac.csv")
        response = self._post_url_response(
            self.book_process_import_url, data, follow=True
        )
        self.assertContains(
            response,
            _(
                "Import finished: {} new, {} updated, {} deleted and {} skipped {}."
            ).format(1, 0, 0, 0, Book._meta.verbose_name_plural),
        )

    @override_settings(TEMPLATE_STRING_IF_INVALID="INVALID_VARIABLE")
    def test_import_second_resource(self):
        Book.objects.create(id=1)

        # GET the import form
        response = self._get_url_response(
            self.book_import_url, str_in_response="Export/Import only book names"
        )
        self.assertTemplateUsed(response, self.admin_import_template_url)
        self.assertContains(response, 'form action=""')

        response = self._do_import_post(self.book_import_url, "books.csv", resource=1)
        self.assertIn("result", response.context)
        self.assertFalse(response.context["result"].has_errors())
        self.assertIn("confirm_form", response.context)
        confirm_form = response.context["confirm_form"]

        data = confirm_form.initial
        self.assertEqual(data["original_file_name"], "books.csv")
        response = self._post_url_response(
            self.book_process_import_url, data, follow=True
        )
        self.assertContains(
            response,
            _(
                "Import finished: {} new, {} updated, {} deleted and {} skipped {}."
            ).format(0, 1, 0, 0, Book._meta.verbose_name_plural),
        )
        # Check, that we really use second resource - author_email didn't get imported
        self.assertEqual(Book.objects.get(id=1).author_email, "")


class ImportLogEntryTest(AdminTestMixin, TestCase):
    def test_import_log_entry(self):
        response = self._do_import_post(self.book_import_url, "books.csv")

        self.assertEqual(response.status_code, 200)
        confirm_form = response.context["confirm_form"]
        data = confirm_form.initial
        self._post_url_response(self.book_process_import_url, data, follow=True)
        book = LogEntry.objects.latest("id")
        self.assertEqual(book.object_repr, "Some book")
        self.assertEqual(book.object_id, str(1))

    def test_import_log_entry_with_fk(self):
        Parent.objects.create(id=1234, name="Some Parent")
        response = self._do_import_post(self.child_import_url, "child.csv")
        self.assertEqual(response.status_code, 200)
        confirm_form = response.context["confirm_form"]
        data = confirm_form.initial
        self._post_url_response(self.child_process_import_url, data, follow=True)
        child = LogEntry.objects.latest("id")
        self.assertEqual(child.object_repr, "Some - child of Some Parent")
        self.assertEqual(child.object_id, str(1))

    @patch("import_export.resources.Resource.skip_row")
    def test_import_log_entry_skip_row(self, mock_skip_row):
        # test issue 1937 - ensure that skipped rows do not create log entries
        mock_skip_row.return_value = True
        response = self._do_import_post(self.book_import_url, "books.csv")

        self.assertEqual(response.status_code, 200)
        confirm_form = response.context["confirm_form"]
        data = confirm_form.initial
        self._post_url_response(self.book_process_import_url, data, follow=True)
        self.assertEqual(0, LogEntry.objects.count())

    def test_import_log_entry_error_row(self):
        # ensure that error rows do not create log entries
        response = self._do_import_post(self.book_import_url, "books.csv")

        self.assertEqual(response.status_code, 200)
        confirm_form = response.context["confirm_form"]
        data = confirm_form.initial
        with mock.patch("core.admin.BookResource.skip_row") as mock_skip:
            mock_skip.side_effect = ValueError("some unknown error")
            self._post_url_response(self.book_process_import_url, data, follow=True)
        self.assertEqual(0, LogEntry.objects.count())

    def test_import_log_entry_validation_error_row(self):
        # ensure that validation error rows do not create log entries
        response = self._do_import_post(self.book_import_url, "books.csv")

        self.assertEqual(response.status_code, 200)
        confirm_form = response.context["confirm_form"]
        data = confirm_form.initial
        with mock.patch("core.admin.BookResource.skip_row") as mock_skip:
            mock_skip.side_effect = ValidationError("some unknown error")
            self._post_url_response(self.book_process_import_url, data, follow=True)
        self.assertEqual(0, LogEntry.objects.count())

    @override_settings(IMPORT_EXPORT_SKIP_ADMIN_LOG=True)
    def test_import_log_entry_skip_admin_log(self):
        response = self._do_import_post(self.book_import_url, "books.csv")

        self.assertEqual(response.status_code, 200)
        confirm_form = response.context["confirm_form"]
        data = confirm_form.initial
        self._post_url_response(self.book_process_import_url, data, follow=True)
        self.assertEqual(0, LogEntry.objects.count())

    def test_import_log_entry_skip_admin_log_attr(self):
        response = self._do_import_post(self.book_import_url, "books.csv")

        self.assertEqual(response.status_code, 200)
        confirm_form = response.context["confirm_form"]
        data = confirm_form.initial
        with mock.patch(
            "import_export.admin.ImportMixin.skip_admin_log",
            new_callable=PropertyMock,
            return_value=True,
        ):
            self._post_url_response(self.book_process_import_url, data, follow=True)
        self.assertEqual(0, LogEntry.objects.count())


@override_settings(IMPORT_EXPORT_SKIP_ADMIN_CONFIRM=True)
class TestImportSkipConfirm(AdminTestMixin, TransactionTestCase):
    fixtures = ["author"]

    def _is_str_in_response(
        self,
        filename,
        input_format,
        encoding=None,
        str_in_response=None,
        follow=False,
        status_code=200,
    ):
        response = self._do_import_post(
            self.book_import_url,
            filename,
            input_format,
            encoding=encoding,
            follow=follow,
        )
        self.assertEqual(response.status_code, status_code)
        if str_in_response is not None:
            self.assertContains(response, str_in_response)

    def _is_regex_in_response(
        self,
        filename,
        input_format,
        encoding=None,
        regex_in_response=None,
        follow=False,
        status_code=200,
    ):
        response = self._do_import_post(
            self.book_import_url,
            filename,
            input_format,
            encoding=encoding,
            follow=follow,
        )
        self.assertEqual(response.status_code, status_code)
        if regex_in_response is not None:
            self.assertRegex(response.content.decode(), regex_in_response)

    def test_import_action_create(self):
        self._is_str_in_response(
            "books.csv",
            "0",
            follow=True,
            str_in_response="Import finished: 1 new, 0 updated, "
            + "0 deleted and 0 skipped books.",
        )
        self.assertEqual(1, Book.objects.count())

    def test_import_action_error_on_save(self):
        with mock.patch("core.models.Book.save") as mock_save:
            mock_save.side_effect = ValueError("some unknown error")
            response = self._do_import_post(self.book_import_url, "books.csv")
        self.assertIn("some unknown error", response.content.decode())

    @override_settings(IMPORT_EXPORT_USE_TRANSACTIONS=True)
    def test_import_transaction_enabled_validation_error(self):
        # with transactions enabled, a validation error should cause the entire
        # import to be rolled back
        self._do_import_post(self.book_import_url, "books-invalid-date.csv")
        self.assertEqual(0, Book.objects.count())

    @override_settings(IMPORT_EXPORT_USE_TRANSACTIONS=False)
    def test_import_transaction_disabled_validation_error(self):
        # with transactions disabled, a validation error should not cause the entire
        # import to fail
        self._do_import_post(self.book_import_url, "books-invalid-date.csv")
        self.assertEqual(1, Book.objects.count())

    @override_settings(IMPORT_EXPORT_USE_TRANSACTIONS=True)
    def test_import_transaction_enabled_core_error(self):
        # test that if we send a file with multiple rows,
        # and transactions is enabled, a core error means that
        # no instances are persisted
        index = self._get_input_format_index("json")
        with mock.patch("core.admin.BookResource.skip_row") as mock_skip:
            mock_skip.side_effect = [None, ValueError("some unknown error"), None]
            response = self._do_import_post(self.book_import_url, "books.json", index)
        self.assertIn("some unknown error", response.content.decode())
        self.assertEqual(0, Book.objects.count())

    @override_settings(IMPORT_EXPORT_USE_TRANSACTIONS=False)
    def test_import_transaction_disabled_core_error(self):
        # with transactions disabled, a core (db constraint) error should not cause the
        # entire import to fail
        index = self._get_input_format_index("json")
        with mock.patch("core.admin.BookResource.skip_row") as mock_skip:
            mock_skip.side_effect = [None, ValueError("some unknown error"), None]
            response = self._do_import_post(self.book_import_url, "books.json", index)
        self.assertIn("some unknown error", response.content.decode())
        self.assertEqual(2, Book.objects.count())

    def test_import_action_mac(self):
        self._is_str_in_response(
            "books-mac.csv",
            "0",
            follow=True,
            str_in_response="Import finished: 1 new, 0 updated, "
            + "0 deleted and 0 skipped books.",
        )

    def test_import_action_iso_8859_1(self):
        self._is_str_in_response(
            "books-ISO-8859-1.csv",
            "0",
            "ISO-8859-1",
            follow=True,
            str_in_response="Import finished: 1 new, 0 updated, "
            + "0 deleted and 0 skipped books.",
        )

    def test_import_action_decode_error(self):
        # attempting to read a file with the incorrect encoding should raise an error
        self._is_regex_in_response(
            "books-ISO-8859-1.csv",
            "0",
            follow=True,
            encoding="utf-8-sig",
            regex_in_response=(
                ".*UnicodeDecodeError.* encountered " "while trying to read file"
            ),
        )

    def test_import_action_binary(self):
        self._is_str_in_response(
            "books.xls",
            "1",
            follow=True,
            str_in_response="Import finished: 1 new, 0 updated, "
            + "0 deleted and 0 skipped books.",
        )


class ConfirmImportPreviewOrderTest(AdminTestMixin, TestCase):
    """Test preview order displayed correctly (issue 1784)."""

    fixtures = ["author"]

    def test_import_preview_order(self):
        author_id = Author.objects.first().id
        response = self._do_import_post(
            self.ebook_import_url,
            "ebooks.csv",
            input_format="0",
            data={"author": author_id},
        )
        # test header rendered in correct order
        target_header_re = (
            r"<thead>[\\n\s]+"
            r"<tr>[\\n\s]+"
            r"<th></th>[\\n\s]+"
            r"<th>id</th>[\\n\s]+"
            r"<th>Email of the author</th>[\\n\s]+"
            r"<th>name</th>[\\n\s]+"
            r"<th>published_date</th>[\\n\s]+"
            r"<th>Author Name</th>[\\n\s]+"
            r"</tr>[\\n\s]+"
            "</thead>"
        )
        self.assertRegex(response.content.decode(), target_header_re)
        # test row rendered in correct order
        target_row_re = (
            r'<tr class="new">[\\n\s]+'
            r'<td class="import-type">[\\n\s]+New[\\n\s]+</td>[\\n\s]+'
            r'<td><ins style="background:#e6ffe6;">1</ins></td>[\\n\s]+'
            r'<td><ins style="background:#e6ffe6;">test@example.com</ins></td>[\\n\s]+'
            r'<td><ins style="background:#e6ffe6;">Some book</ins></td>[\\n\s]+'
            r"<td></td>[\\n\s]+"
            r"<td></td>[\\n\s]+"
            "</tr>"
        )
        self.assertRegex(response.content.decode(), target_row_re)


class CustomColumnNameImportTest(AdminTestMixin, TestCase):
    """Handle custom column name import (issue 1822)."""

    fixtures = ["author"]

    def setUp(self):
        super().setUp()
        EBookResource._meta.fields = ("id", "author_email", "name", "published_date")

    def tearDown(self):
        super().tearDown()
        EBookResource._meta.fields = ("id", "author_email", "name", "published")

    def test_import_preview_order(self):
        author_id = Author.objects.first().id
        response = self._do_import_post(
            self.ebook_import_url,
            "ebooks.csv",
            input_format="0",
            data={"author": author_id},
        )
        # test header rendered in correct order
        target_header_re = (
            r"<thead>[\\n\s]+"
            r"<tr>[\\n\s]+"
            r"<th></th>[\\n\s]+"
            r"<th>id</th>[\\n\s]+"
            r"<th>Email of the author</th>[\\n\s]+"
            r"<th>name</th>[\\n\s]+"
            r"<th>published_date</th>[\\n\s]+"
            r"<th>Author Name</th>[\\n\s]+"
            r"</tr>[\\n\s]+"
            "</thead>"
        )
        self.assertRegex(response.content.decode(), target_header_re)
        # test row rendered in correct order
        target_row_re = (
            r'<tr class="new">[\\n\s]+'
            r'<td class="import-type">[\\n\s]+New[\\n\s]+</td>[\\n\s]+'
            r'<td><ins style="background:#e6ffe6;">1</ins></td>[\\n\s]+'
            r'<td><ins style="background:#e6ffe6;">test@example.com</ins></td>[\\n\s]+'
            r'<td><ins style="background:#e6ffe6;">Some book</ins></td>[\\n\s]+'
            r"<td></td>[\\n\s]+"
            r"<td></td>[\\n\s]+"
            "</tr>"
        )
        self.assertRegex(response.content.decode(), target_row_re)


class DefaultFieldsImportOrderTest(AdminTestMixin, TestCase):
    """
    Display correct import order based on default 'fields' declaration (issue 1845).
    Ensure that the prompt text on the import page renders the
    fields in the correct order.
    """

    def test_import_preview_order(self):
        response = self._get_url_response(self.ebook_import_url)
        # test display rendered in correct order
        target_re = (
            r"This importer will import the following fields:[\\n\s]+"
            r"<code>id, Email of the author, name, published_date, Author Name</code>"
            r"[\\n\s]+"
        )
        self.assertRegex(response.content.decode(), target_re)


class DeclaredImportOrderTest(AdminTestMixin, TestCase):
    """
    Display correct import order when 'import_order' is declared (issue 1845).
    Ensure that the prompt text on the import page renders the
    fields in the correct order.
    """

    def setUp(self):
        super().setUp()
        EBookResource._meta.import_order = ("id", "name", "published", "author_email")

    def tearDown(self):
        super().tearDown()
        EBookResource._meta.import_order = ()

    def test_import_preview_order(self):
        response = self._get_url_response(self.ebook_import_url)
        # test display rendered in correct order
        target_re = (
            r"This importer will import the following fields:[\\n\s]+"
            r"<code>id, name, published_date, Email of the author, Author Name</code>"
            r"[\\n\s]+"
        )
        self.assertRegex(response.content.decode(), target_re)
