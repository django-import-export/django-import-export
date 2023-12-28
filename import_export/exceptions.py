class ImportExportError(Exception):
    """A generic exception for all others to extend."""

    pass


class FieldError(ImportExportError):
    """Raised when a field encounters an error."""

    pass


class RowError(ImportExportError):
    """A wrapper for errors thrown from the import process."""

    def __init__(self, error, number=None, row=None):
        self.error = error
        self.number = number
        self.row = row

    def __str__(self):
        return f"{self.number}: {self.error}"
