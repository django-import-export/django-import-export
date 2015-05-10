# -*- coding: utf-8 -*-
import os

from django.test import TestCase
from django.core.cache import cache
from django.core.files.storage import default_storage
from import_export.tmp_storages import TempFolderStorage, CacheStorage, MediaStorage


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
        self.assertEqual(self.test_string.decode('utf-8'), tmp_storage.read())

        self.assertTrue(os.path.isfile(tmp_storage.get_full_path()))
        tmp_storage.remove()
        self.assertFalse(os.path.isfile(tmp_storage.get_full_path()))

    def test_cache_storage(self):
        tmp_storage = CacheStorage()
        tmp_storage.save(self.test_string)
        name = tmp_storage.name

        tmp_storage = CacheStorage(name=name)
        self.assertEqual(self.test_string, tmp_storage.read())

        self.assertNotEqual(cache.get(tmp_storage.CACHE_PREFIX, tmp_storage.name), None)
        tmp_storage.remove()
        self.assertEqual(cache.get(tmp_storage.name), None)

    def test_media_storage(self):
        tmp_storage = MediaStorage()
        tmp_storage.save(self.test_string)
        name = tmp_storage.name

        tmp_storage = MediaStorage(name=name)
        self.assertEqual(self.test_string, tmp_storage.read())

        self.assertTrue(default_storage.exists(tmp_storage.get_full_path()))
        tmp_storage.remove()
        self.assertFalse(default_storage.exists(tmp_storage.get_full_path()))
