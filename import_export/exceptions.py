from __future__ import unicode_literals


class ImportExportError(Exception):
    """A generic exception for all others to extend."""
    pass


class FieldError(ImportExportError):
    """Raised when a field encounters an error."""
    pass


class AsyncExportError(ImportExportError):
    """Raised when there is an error exporting data asynchronously"""
    pass
