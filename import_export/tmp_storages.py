import os
import tempfile
from uuid import uuid4

from django.core.cache import cache
from django.core.files.base import ContentFile


class BaseStorage:
    """
    Base class for temporary storage of uploaded import files.

    Storages deal in ``bytes`` only: :meth:`save` receives the raw uploaded
    data and :meth:`read` returns it unchanged.  Decoding text formats is the
    responsibility of the :class:`~import_export.formats.base_formats.Format`.
    """

    _REMOVED_KWARGS = ("read_mode", "encoding")

    def __init__(self, **kwargs):
        for kwarg in self._REMOVED_KWARGS:
            if kwarg in kwargs:
                raise TypeError(
                    f"'{kwarg}' is no longer supported by {type(self).__name__}: "
                    "storages read and write bytes only (see the v5 release notes)."
                )
        self.name = kwargs.get("name", None)

    def save(self, data):
        raise NotImplementedError

    def read(self):
        raise NotImplementedError

    def remove(self):
        raise NotImplementedError


class TempFolderStorage(BaseStorage):
    def save(self, data):
        with self._open(mode="wb") as file:
            file.write(data)

    def read(self):
        with self._open(mode="rb") as file:
            return file.read()

    def remove(self):
        os.remove(self.get_full_path())

    def get_full_path(self):
        return os.path.join(tempfile.gettempdir(), self.name)

    def _open(self, mode="rb"):
        if self.name:
            return open(self.get_full_path(), mode)
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
    _storage = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._configure_storage()
        self.MEDIA_FOLDER = kwargs.get("MEDIA_FOLDER", "django-import-export")

    def _configure_storage(self):
        from django.core.files.storage import StorageHandler

        sh = StorageHandler()
        self._storage = (
            sh["import_export"] if "import_export" in sh.backends else sh["default"]
        )

    def save(self, data):
        if not self.name:
            self.name = uuid4().hex
        self._storage.save(self.get_full_path(), ContentFile(data))

    def read(self):
        with self._storage.open(self.get_full_path(), mode="rb") as f:
            return f.read()

    def remove(self):
        self._storage.delete(self.get_full_path())

    def get_full_path(self):
        if self.MEDIA_FOLDER is not None:
            return os.path.join(self.MEDIA_FOLDER, self.name)
        return self.name
