from __future__ import unicode_literals


class ImportExportError(Exception):
    """A generic exception for all others to extend."""
    pass


class FieldError(ImportExportError):
    """Raised when a field encounters an error."""
    pass


class SkipRow(ImportExportError):
    """Raised when exporting a row that should be skipped"""
    pass
