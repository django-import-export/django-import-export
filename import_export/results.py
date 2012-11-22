class RowResult(object):

    def __init__(self):
        self.errors = []
        self.orig_fields = []
        self.fields = []

    def combined_fields(self):
        return zip(self.orig_fields, self.fields)


class Result(object):

    def __init__(self, *args, **kwargs):
        super(Result, self).__init__(*args, **kwargs)
        self.base_errors = []
        self.rows = []

    def row_errors(self):
        return [(i + 1, row.errors)
                for i, row in enumerate(self.rows) if row.errors]

    def has_errors(self):
        return self.base_errors or self.row_errors()
