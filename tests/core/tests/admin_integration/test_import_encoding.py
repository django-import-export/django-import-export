from core.tests.admin_integration.mixins import AdminTestMixin
from django.test.testcases import TestCase
from django.test.utils import override_settings


class ConfirmImportEncodingTest(AdminTestMixin, TestCase):
    """Test handling 'confirm import' step using different file encodings
    and storage types.
    """

    def _is_str_in_response(self, filename, input_format, encoding=None):
        super()._assert_string_in_response(
            self.book_import_url,
            filename,
            input_format,
            encoding=encoding,
            str_in_response="test@example.com",
        )

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.TempFolderStorage"
    )
    def test_import_action_handles_TempFolderStorage_read(self):
        self._is_str_in_response("books.csv", "0")

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.TempFolderStorage"
    )
    def test_import_action_handles_TempFolderStorage_read_mac(self):
        self._is_str_in_response("books-mac.csv", "0")

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.TempFolderStorage"
    )
    def test_import_action_handles_TempFolderStorage_read_iso_8859_1(self):
        self._is_str_in_response("books-ISO-8859-1.csv", "0", "ISO-8859-1")

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.TempFolderStorage"
    )
    def test_import_action_handles_TempFolderStorage_read_binary(self):
        self._is_str_in_response("books.xls", "1")

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.CacheStorage"
    )
    def test_import_action_handles_CacheStorage_read(self):
        self._is_str_in_response("books.csv", "0")

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.CacheStorage"
    )
    def test_import_action_handles_CacheStorage_read_mac(self):
        self._is_str_in_response("books-mac.csv", "0")

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.CacheStorage"
    )
    def test_import_action_handles_CacheStorage_read_iso_8859_1(self):
        self._is_str_in_response("books-ISO-8859-1.csv", "0", "ISO-8859-1")

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.CacheStorage"
    )
    def test_import_action_handles_CacheStorage_read_binary(self):
        self._is_str_in_response("books.xls", "1")

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.MediaStorage"
    )
    def test_import_action_handles_MediaStorage_read(self):
        self._is_str_in_response("books.csv", "0")

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.MediaStorage"
    )
    def test_import_action_handles_MediaStorage_read_mac(self):
        self._is_str_in_response("books-mac.csv", "0")

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.MediaStorage"
    )
    def test_import_action_handles_MediaStorage_read_iso_8859_1(self):
        self._is_str_in_response("books-ISO-8859-1.csv", "0", "ISO-8859-1")

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.MediaStorage"
    )
    def test_import_action_handles_MediaStorage_read_binary(self):
        self._is_str_in_response("books.xls", "1")


class CompleteImportEncodingTest(AdminTestMixin, TestCase):
    """Test handling 'complete import' step using different file encodings
    and storage types.
    """

    def _is_str_in_response(self, filename, input_format, encoding=None):
        response = self._do_import_post(
            self.book_import_url, filename, input_format, encoding=encoding
        )
        confirm_form = response.context["confirm_form"]
        data = confirm_form.initial
        response = self._post_url_response(
            self.book_process_import_url, data, follow=True
        )
        self.assertContains(
            response,
            "Import finished: 1 new, 0 updated, 0 deleted and 0 skipped books.",
        )

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.TempFolderStorage"
    )
    def test_import_action_handles_TempFolderStorage_read(self):
        self._is_str_in_response("books.csv", "0")

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.TempFolderStorage"
    )
    def test_import_action_handles_TempFolderStorage_read_mac(self):
        self._is_str_in_response("books-mac.csv", "0")

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.TempFolderStorage"
    )
    def test_import_action_handles_TempFolderStorage_read_iso_8859_1(self):
        self._is_str_in_response("books-ISO-8859-1.csv", "0", "ISO-8859-1")

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.TempFolderStorage"
    )
    def test_import_action_handles_TempFolderStorage_read_binary(self):
        self._is_str_in_response("books.xls", "1")

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.CacheStorage"
    )
    def test_import_action_handles_CacheStorage_read(self):
        self._is_str_in_response("books.csv", "0")

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.CacheStorage"
    )
    def test_import_action_handles_CacheStorage_read_mac(self):
        self._is_str_in_response("books-mac.csv", "0")

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.CacheStorage"
    )
    def test_import_action_handles_CacheStorage_read_iso_8859_1(self):
        self._is_str_in_response("books-ISO-8859-1.csv", "0", "ISO-8859-1")

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.CacheStorage"
    )
    def test_import_action_handles_CacheStorage_read_binary(self):
        self._is_str_in_response("books.xls", "1")

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.MediaStorage"
    )
    def test_import_action_handles_MediaStorage_read(self):
        self._is_str_in_response("books.csv", "0")

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.MediaStorage"
    )
    def test_import_action_handles_MediaStorage_read_mac(self):
        self._is_str_in_response("books-mac.csv", "0")

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.MediaStorage"
    )
    def test_import_action_handles_MediaStorage_read_iso_8859_1(self):
        self._is_str_in_response("books-ISO-8859-1.csv", "0", "ISO-8859-1")

    @override_settings(
        IMPORT_EXPORT_TMP_STORAGE_CLASS="import_export.tmp_storages.MediaStorage"
    )
    def test_import_action_handles_MediaStorage_read_binary(self):
        self._is_str_in_response("books.xls", "1")
