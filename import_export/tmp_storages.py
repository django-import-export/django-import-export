import os
import tempfile
from uuid import uuid4

from django.core.cache import cache
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage


class BaseStorage:

    def __init__(self, name=None, encoding=None):
        self.name = name
        self.encoding = encoding

    def save(self, data, mode='w'):
        raise NotImplementedError

    def read(self, read_mode='r'):
        raise NotImplementedError

    def remove(self):
        raise NotImplementedError


class TempFolderStorage(BaseStorage):

    def open(self, mode='r'):
        if self.name:
            return open(self.get_full_path(), mode, encoding=self.encoding)
        else:
            tmp_file = tempfile.NamedTemporaryFile(delete=False)
            self.name = tmp_file.name
            return tmp_file

    def save(self, data, mode='w'):
        with self.open(mode=mode) as file:
            file.write(data)

    def read(self, mode='r'):
        with self.open(mode=mode) as file:
            return file.read()

    def remove(self):
        os.remove(self.get_full_path())

    def get_full_path(self):
        return os.path.join(
            tempfile.gettempdir(),
            self.name
        )


class CacheStorage(BaseStorage):
    """
    By default memcache maximum size per key is 1MB, be careful with large files.
    """
    CACHE_LIFETIME = 86400
    CACHE_PREFIX = 'django-import-export-'

    def save(self, data, mode=None):
        if not self.name:
            self.name = uuid4().hex
        cache.set(self.CACHE_PREFIX + self.name, data, self.CACHE_LIFETIME)

    def read(self, read_mode='r'):
        data = cache.get(self.CACHE_PREFIX + self.name)
        if isinstance(data, bytes) and self.encoding is not None:
            data = data.decode(self.encoding)
        return data

    def remove(self):
        cache.delete(self.name)


class MediaStorage(BaseStorage):
    MEDIA_FOLDER = 'django-import-export'

    def save(self, data, mode=None):
        if not self.name:
            self.name = uuid4().hex
        # data is stored in correct encoding within ContentFile
        # so it doesn't have to be decoded in read()
        default_storage.save(self.get_full_path(), ContentFile(data))

    def read(self, read_mode='rb'):
        with default_storage.open(self.get_full_path(), mode=read_mode) as f:
            return f.read()

    def remove(self):
        default_storage.delete(self.get_full_path())

    def get_full_path(self):
        return os.path.join(
            self.MEDIA_FOLDER,
            self.name
        )
