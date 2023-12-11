import os
import tempfile
from uuid import uuid4

import django
from django.conf import settings
from django.core.cache import cache
from django.core.files.base import ContentFile


class BaseStorage:
    def __init__(self, **kwargs):
        self.name = kwargs.get("name", None)
        self.read_mode = kwargs.get("read_mode", "r")
        self.encoding = kwargs.get("encoding", None)

    def save(self, data):
        raise NotImplementedError

    def read(self):
        raise NotImplementedError

    def remove(self):
        raise NotImplementedError


class TempFolderStorage(BaseStorage):
    def save(self, data):
        with self._open(mode="w") as file:
            file.write(data)

    def read(self):
        with self._open(mode=self.read_mode) as file:
            return file.read()

    def remove(self):
        os.remove(self.get_full_path())

    def get_full_path(self):
        return os.path.join(tempfile.gettempdir(), self.name)

    def _open(self, mode="r"):
        if self.name:
            return open(self.get_full_path(), mode, encoding=self.encoding)
        else:
            tmp_file = tempfile.NamedTemporaryFile(delete=False)
            self.name = tmp_file.name
            return tmp_file


class CacheStorage(BaseStorage):
    """
    By default memcache maximum size per key is 1MB, be careful with large files.
    """

    CACHE_LIFETIME = 86400
    CACHE_PREFIX = "django-import-export-"

    def save(self, data):
        if not self.name:
            self.name = uuid4().hex
        cache.set(self.CACHE_PREFIX + self.name, data, self.CACHE_LIFETIME)

    def read(self):
        return cache.get(self.CACHE_PREFIX + self.name)

    def remove(self):
        cache.delete(self.CACHE_PREFIX + self.name)


class MediaStorage(BaseStorage):
    MEDIA_FOLDER = "django-import-export"
    _storage = None

    def __init__(self, **kwargs):
        if django.VERSION >= (4, 2):
            from django.core.files.storage import StorageHandler

            sh = StorageHandler()
            if "import_export" in sh.backends:
                self._storage = sh["import_export"]
            else:
                self._storage = sh["default"]
        else:
            from django.core.files.storage import default_storage

            self._storage = getattr(
                settings, "IMPORT_EXPORT_DEFAULT_FILE_STORAGE", default_storage
            )

        # issue 1589 - Ensure that for MediaStorage, we read in binary mode
        kwargs.update({"read_mode": "rb"})
        super().__init__(**kwargs)

    def save(self, data):
        if not self.name:
            self.name = uuid4().hex
        self._storage.save(self.get_full_path(), ContentFile(data))

    def read(self):
        with self._storage.open(self.get_full_path(), mode=self.read_mode) as f:
            return f.read()

    def remove(self):
        self._storage.delete(self.get_full_path())

    def get_full_path(self):
        return os.path.join(self.MEDIA_FOLDER, self.name)
