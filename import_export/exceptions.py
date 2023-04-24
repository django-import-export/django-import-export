class ImportExportError(Exception):
    """A generic exception for all others to extend."""

    pass


class FieldError(ImportExportError):
    """Raised when a field encounters an error."""

    pass
