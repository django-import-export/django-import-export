import sys
import traceback
from collections import OrderedDict

import tablib

from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import ugettext_lazy as _

from .instance_loader import (
        ModelInstanceLoader,
        )


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


class Importer(object):
    model = None
    format = None
    import_code = "ID"
    raise_errors = False
    dry_run = True
    mapping = None
    from_encoding = None
    instance_loader_class = ModelInstanceLoader

    def __init__(self, f=None, **kwargs):
        self.f = f
        for key, value in kwargs.iteritems():
            setattr(self, key, value)
        self.instance_loader = self.instance_loader_class(self)

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

    def init_instance(self, row):
        return self.model()

    def get_instance(self, row):
        return self.instance_loader.get_instance(row)

    def get_or_init_instance(self, row):
        instance = self.get_instance(row)
        if instance:
            return (instance, False)
        else:
            return (self.init_instance(row), True)

    def set_instance_attr(self, instance, row, field):
        setattr(instance, self.get_mapping()[field], row[field])

    def save_instance(self, instance):
        if not self.dry_run:
            instance.save()

    def before_save_instance(self, instance, new):
        """
        Override to add additional logic.
        """
        pass

    def after_save_instance(self, instance, new):
        """
        Override to add additional logic.
        """
        pass

    def get_representation(self, instance, orig):
        values = []
        for f in self.get_mapping().values():
            try:
                values.append(unicode(getattr(instance, f)))
            except ObjectDoesNotExist:
                values.append("")
        return values

    def get_representation_fields(self):
        """
        Fields to show in preview.
        """
        return self.get_mapping().keys()

    def run(self):
        result = Result()
        try:
            self.load_dataset()
        except Exception, e:
            tb_info = traceback.format_exc(sys.exc_info()[2])
            result.base_errors.append(_('Loading error') +
                    u': %s (%s)' % (repr(e), tb_info))
            if self.raise_errors:
                raise
            return result

        for row in self.data.dict:
            try:
                row_result = RowResult()
                instance, new = self.get_or_init_instance(row)
                row_result.orig_fields = self.get_representation(instance,
                        True)
                for field in self.get_mapping().keys():
                    self.set_instance_attr(instance, row, field)
                self.before_save_instance(instance, new)
                self.save_instance(instance)
                self.after_save_instance(instance, new)
                row_result.fields = self.get_representation(instance, False)
            except Exception, e:
                tb_info = traceback.format_exc(sys.exc_info()[2])
                row_result.errors.append('%s: %s' % (repr(e), tb_info))
                if self.raise_errors:
                    raise
            result.rows.append(row_result)
        return result

    def get_export_representation(self, obj):
        return self.get_representation(obj, True)

    def get_export_headers(self):
        headers = [unicode(k) for k in self.get_mapping().keys()]
        return headers

    def export(self, queryset):
        headers = self.get_export_headers()
        data = tablib.Dataset(headers)
        for obj in queryset:
            data.append(self.get_export_representation(obj))
        return data
