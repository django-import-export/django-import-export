from collections import OrderedDict

import tablib

from django.utils.translation import ugettext_lazy as _


class RowResult(object):

    def __init__(self):
        self.errors = []
        self.orig_fields = []
        self.fields = []

    def combined_fields(self):
        return zip(self.orig_fields, self.fields)


class Result(list):

    def __init__(self, *args, **kwargs):
        super(Result, self).__init__(*args, **kwargs)
        self.base_errors = []

    def row_errors(self):
        return [(i + 1, row.errors)
                for i, row in enumerate(self) if row.errors]

    def has_errors(self):
        return self.base_errors or self.row_errors()


class Importer(object):
    model = None
    format = None
    import_code = "ID"
    raise_errors = False
    dry_run = True
    mapping = None
    from_encoding = None

    def __init__(self, f=None, **kwargs):
        self.f = f
        for key, value in kwargs.iteritems():
            setattr(self, key, value)

    def set_stream(self, f):
        self.f = f

    def get_mapping(self):
        if self.mapping:
            return self.mapping
        mapping = [(f.verbose_name, f.name) for f in self.model._meta.fields]
        return OrderedDict(mapping)

    def load_dataset(self):
        if self.from_encoding:
            text = unicode(self.f.read(), self.from_encoding).encode('utf-8')
        else:
            text = self.f.read()
        if not self.format:
            self.data = tablib.import_set(text)
        else:
            self.data = tablib.Dataset()
            self.format.import_set(self.data, text)

    def get_instance(self, row):
        return self.model.objects.get(**{
            self.get_mapping()[self.import_code]: row[self.import_code]
            })

    def init_instance(self, row):
        return self.model()

    def get_or_init_instance(self, row):
        try:
            instance = self.get_instance(row)
        except self.model.DoesNotExist:
            instance = self.init_instance(row)
        return instance

    def set_instance_attr(self, instance, row, field):
        setattr(instance, self.get_mapping()[field], row[field])

    def save_instance(self, instance):
        if not self.dry_run:
            instance.save()

    def get_representation(self, instance):
        return [unicode(getattr(instance, f))
                for f in self.get_mapping().values()]

    def run(self):
        result = Result()
        try:
            self.load_dataset()
        except Exception, e:
            result.base_errors.append(_('Loading error') +
                    u': %s' % repr(e))
            if self.raise_errors:
                raise
            return result

        for row in self.data.dict:
            try:
                row_result = RowResult()
                instance = self.get_or_init_instance(row)
                row_result.orig_fields = self.get_representation(instance)
                for field in self.get_mapping().keys():
                    self.set_instance_attr(instance, row, field)
                self.save_instance(instance)
                row_result.fields = self.get_representation(instance)
            except Exception, e:
                row_result.errors.append(repr(e))
                if self.raise_errors:
                    raise
            result.append(row_result)
        return result
