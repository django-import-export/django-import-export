import io
import os
from unittest.mock import mock_open, patch

from django.core.cache import cache
from django.core.files.storage import FileSystemStorage, default_storage
from django.test import TestCase
from django.test.utils import override_settings

from import_export.tmp_storages import (
    BaseStorage,
    CacheStorage,
    MediaStorage,
    TempFolderStorage,
)


class TestBaseStorage(TestCase):
    def setUp(self):
        self.storage = BaseStorage()

    def test_save(self):
        with self.assertRaises(NotImplementedError):
            self.storage.save(None)

    def test_read(self):
        with self.assertRaises(NotImplementedError):
            self.storage.read()

    def test_remove(self):
        with self.assertRaises(NotImplementedError):
            self.storage.remove()


class TestTempFolderStorage(TempFolderStorage):
    def get_full_path(self):
        return "/tmp/f"


class TestMediaStorage(MediaStorage):
    def get_full_path(self):
        return "f"


class TempStoragesTest(TestCase):
    def setUp(self):
        self.test_string = b"""
id,name,author,author_email,imported,published,price,categories
2,Bar,1,,0,,,
1,Foo,,,0,,,
"""

    def test_temp_folder_storage(self):
        tmp_storage = TempFolderStorage()
        tmp_storage.save(self.test_string)
        name = tmp_storage.name

        tmp_storage = TempFolderStorage(name=name)
        self.assertEqual(self.test_string, tmp_storage.read())

        self.assertTrue(os.path.isfile(tmp_storage.get_full_path()))
        tmp_storage.remove()
        self.assertFalse(os.path.isfile(tmp_storage.get_full_path()))

    def test_temp_folder_storage_reads_binary(self):
        tmp_storage = TestTempFolderStorage()
        tmp_storage.name = "f"
        with patch("builtins.open", mock_open(read_data=b"data")) as mock_file:
            self.assertEqual(b"data", tmp_storage.read())
            mock_file.assert_called_with("/tmp/f", "rb")

    def test_temp_folder_storage_writes_binary(self):
        tmp_storage = TestTempFolderStorage()
        tmp_storage.name = "f"
        with patch("builtins.open", mock_open()) as mock_file:
            tmp_storage.save(b"data")
            mock_file.assert_called_with("/tmp/f", "wb")
            mock_file().write.assert_called_with(b"data")

    def test_cache_storage(self):
        tmp_storage = CacheStorage()
        tmp_storage.save(self.test_string)
        name = tmp_storage.name

        tmp_storage = CacheStorage(name=name)
        self.assertEqual(self.test_string, tmp_storage.read())

        self.assertIsNotNone(cache.get(tmp_storage.CACHE_PREFIX + tmp_storage.name))
        tmp_storage.remove()
        self.assertIsNone(cache.get(tmp_storage.CACHE_PREFIX + tmp_storage.name))

    def test_cache_storage_read_by_name(self):
        tmp_storage = CacheStorage()
        tmp_storage.name = "f"
        cache.set("django-import-export-f", b"101")
        res = tmp_storage.read()
        self.assertEqual(b"101", res)

    def test_cache_storage_round_trips_unicode_bytes(self):
        tmp_storage = CacheStorage()
        tmp_storage.name = "f"
        data = "àèìòùçñ".encode()
        tmp_storage.save(data)
        res = tmp_storage.read()
        self.assertEqual(data, res)

    def test_media_storage(self):
        tmp_storage = MediaStorage()
        tmp_storage.save(self.test_string)
        name = tmp_storage.name

        tmp_storage = MediaStorage(name=name)
        self.assertEqual(self.test_string, tmp_storage.read())

        self.assertTrue(default_storage.exists(tmp_storage.get_full_path()))
        tmp_storage.remove()
        self.assertFalse(default_storage.exists(tmp_storage.get_full_path()))

    def test_media_storage_reads_binary(self):
        tmp_storage = TestMediaStorage()
        tmp_storage.name = "f"
        with patch.object(FileSystemStorage, "open") as mock_open:
            tmp_storage.read()
            mock_open.assert_called_with("f", mode="rb")


class CustomizedStorage:
    save_count = 0
    open_count = 0
    delete_count = 0

    def __init__(self, **kwargs):
        pass

    def save(self, path, data):
        self.save_count += 1

    def open(self, path, mode=None):
        self.open_count += 1
        return io.StringIO("a")

    def delete(self, path):
        self.delete_count += 1


class CustomizedMediaStorageTestDjango(TestCase):
    @override_settings(
        STORAGES={
            "import_export": {
                "BACKEND": "tests.core.tests.test_tmp_storages.CustomizedStorage"
            }
        }
    )
    def test_MediaStorage_uses_custom_storage_implementation(self):
        tmp_storage = TestMediaStorage()
        tmp_storage.save(b"a")
        self.assertEqual(1, tmp_storage._storage.save_count)
        tmp_storage.read()
        self.assertEqual(1, tmp_storage._storage.open_count)
        tmp_storage.remove()
        self.assertEqual(1, tmp_storage._storage.delete_count)

    @override_settings(
        STORAGES={
            "import_export": {
                "BACKEND": "tests.core.tests.test_tmp_storages.CustomizedStorage"
            }
        }
    )
    def test_disable_media_folder(self):
        tmp_storage = MediaStorage(MEDIA_FOLDER=None)
        tmp_storage.name = "TESTNAME"
        self.assertIsNone(tmp_storage.MEDIA_FOLDER)
        self.assertEqual("TESTNAME", tmp_storage.get_full_path())

    def test_media_folder(self):
        tmp_storage = MediaStorage()
        self.assertEqual("django-import-export", tmp_storage.MEDIA_FOLDER)
