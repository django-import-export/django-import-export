class Error(object):

    def __init__(self, error, traceback=None):
        self.error = error
        self.traceback = traceback


class RowResult(object):
    IMPORT_TYPE_UPDATE = 'update'
    IMPORT_TYPE_NEW = 'new'
    IMPORT_TYPE_DELETE = 'delete'
    IMPORT_TYPE_SKIP = 'skip'

    def __init__(self):
        self.errors = []
        self.diff = None
        self.import_type = None


class Result(object):

    def __init__(self, *args, **kwargs):
        super(Result, self).__init__(*args, **kwargs)
        self.base_errors = []
        self.rows = []

    def row_errors(self):
        return [(i + 1, row.errors)
                for i, row in enumerate(self.rows) if row.errors]

    def has_errors(self):
        return bool(self.base_errors or self.row_errors())
