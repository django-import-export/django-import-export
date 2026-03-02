from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("django-import-export-continis")
except PackageNotFoundError:
    __version__ = "0.0.0"
