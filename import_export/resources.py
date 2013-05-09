import functools
from copy import deepcopy
import sys
import traceback

import tablib
from diff_match_patch import diff_match_patch

from django.utils.safestring import mark_safe
from django.utils.datastructures import SortedDict
from django.db import transaction
from django.db.models.related import RelatedObject
from django.conf import settings

from .results import Error, Result, RowResult
from .fields import Field
from import_export import widgets
from .instance_loaders import (
        ModelInstanceLoader,
        )


USE_TRANSACTIONS = getattr(settings, 'IMPORT_EXPORT_USE_TRANSACTIONS', False)


class ResourceOptions(object):
    """
    The inner Meta class allows for class-level configuration of how the
    Resource should behave. The following options are available:

    * ``fields`` - Controls what introspected fields the Resource
      should include. A whitelist of fields.

    * ``exclude`` - Controls what introspected fields the Resource should
      NOT include. A blacklist of fields.

    * ``model`` - Django Model class. It is used to introspect available
      fields.

    * ``instance_loader_class`` - Controls which class instance will take
      care of loading existing objects.

    * ``import_id_fields`` - Controls which object fields will be used to
      identify existing instances.

    * ``export_order`` - Controls export order for columns.

    * ``widgets`` - dictionary defines widget kwargs for fields.

    * ``use_transactions`` - Controls if import should use database
      transactions. Default value is ``None`` meaning
      ``settings.IMPORT_EXPORT_USE_TRANSACTIONS`` will be evaluated.

    """
    fields = None
    model = None
    exclude = None
    instance_loader_class = None
    import_id_fields = ['id']
    export_order = None
    widgets = None
    use_transactions = None

    def __new__(cls, meta=None):
        overrides = {}

        if meta:
            for override_name in dir(meta):
                if not override_name.startswith('_'):
                    overrides[override_name] = getattr(meta, override_name)

        return object.__new__(type('ResourceOptions', (cls,), overrides))


class DeclarativeMetaclass(type):

    def __new__(cls, name, bases, attrs):
        declared_fields = []

        for field_name, obj in attrs.items():
            if isinstance(obj, Field):
                field = attrs.pop(field_name)
                if not field.column_name:
                    field.column_name = field_name
                declared_fields.append((field_name, field))

        attrs['fields'] = SortedDict(declared_fields)
        new_class = super(DeclarativeMetaclass, cls).__new__(cls, name,
                bases, attrs)
        opts = getattr(new_class, 'Meta', None)
        new_class._meta = ResourceOptions(opts)

        return new_class


class Resource(object):
    """
    Resource defines how objects are mapped to their import and export
    representations and handle importing and exporting data.
    """
    __metaclass__ = DeclarativeMetaclass

    def get_use_transactions(self):
        if self._meta.use_transactions is None:
            return USE_TRANSACTIONS
        else:
            return self._meta.use_transactions

    def get_fields(self):
        """
        Returns fields in ``export_order`` order.
        """
        return [self.fields[f] for f in self.get_export_order()]

    def init_instance(self, row=None):
        raise NotImplementedError()

    def get_instance(self, instance_loader, row):
        return instance_loader.get_instance(row)

    def get_or_init_instance(self, instance_loader, row):
        instance = self.get_instance(instance_loader, row)
        if instance:
            return (instance, False)
        else:
            return (self.init_instance(row), True)

    def save_instance(self, instance, dry_run=False):
        self.before_save_instance(instance, dry_run)
        if not dry_run:
            instance.save()
        self.after_save_instance(instance, dry_run)

    def before_save_instance(self, instance, dry_run):
        """
        Override to add additional logic.
        """
        pass

    def after_save_instance(self, instance, dry_run):
        """
        Override to add additional logic.
        """
        pass

    def delete_instance(self, instance, dry_run=False):
        self.before_delete_instance(instance, dry_run)
        if not dry_run:
            instance.delete()
        self.after_delete_instance(instance, dry_run)

    def before_delete_instance(self, instance, dry_run):
        """
        Override to add additional logic.
        """
        pass

    def after_delete_instance(self, instance, dry_run):
        """
        Override to add additional logic.
        """
        pass

    def import_field(self, field, obj, data):
        if field.attribute and field.column_name in data:
            field.save(obj, data)

    def import_obj(self, obj, data):
        """
        """
        for field in self.get_fields():
            if isinstance(field.widget, widgets.ManyToManyWidget):
                continue
            self.import_field(field, obj, data)

    def save_m2m(self, obj, data, dry_run):
        """
        Saves m2m fields.

        Model instance need to have a primary key value before
        a many-to-many relationship can be used.
        """
        if not dry_run:
            for field in self.get_fields():
                if not isinstance(field.widget, widgets.ManyToManyWidget):
                    continue
                self.import_field(field, obj, data)

    def for_delete(self, row, instance):
        """
        Returns ``True`` if ``row`` importing should delete instance.

        Default implementation returns ``False``.
        Override this method to handle deletion.
        """
        return False

    def get_diff(self, original, current, dry_run=False):
        """
        Get diff between original and current object when ``import_data``
        is run.

        ``dry_run`` allows handling special cases when object is not saved
        to database (ie. m2m relationships).
        """
        data = []
        dmp = diff_match_patch()
        for field in self.get_fields():
            v1 = self.export_field(field, original) if original else ""
            v2 = self.export_field(field, current) if current else ""
            diff = dmp.diff_main(unicode(v1), unicode(v2))
            dmp.diff_cleanupSemantic(diff)
            html = dmp.diff_prettyHtml(diff)
            html = mark_safe(html)
            data.append(html)
        return data

    def get_diff_headers(self):
        """
        Diff representation headers.
        """
        return self.get_export_headers()

    def import_data(self, dataset, dry_run=False, raise_errors=False,
            use_transactions=None):
        """
        Imports data from ``dataset``.

        ``use_transactions``
            If ``True`` import process will be processed inside transaction.
            If ``dry_run`` is set, or error occurs, transaction will be rolled
            back.
        """
        result = Result()

        if use_transactions is None:
            use_transactions = self.get_use_transactions()

        if use_transactions is True:
            # when transactions are used we want to create/update/delete object
            # as transaction will be rolled back if dry_run is set
            real_dry_run = False
            transaction.enter_transaction_management()
            transaction.managed(True)
        else:
            real_dry_run = dry_run

        instance_loader = self._meta.instance_loader_class(self, dataset)

        for row in dataset.dict:
            try:
                row_result = RowResult()
                instance, new = self.get_or_init_instance(instance_loader, row)
                if new:
                    row_result.import_type = RowResult.IMPORT_TYPE_NEW
                else:
                    row_result.import_type = RowResult.IMPORT_TYPE_UPDATE
                row_result.new_record = new
                original = deepcopy(instance)
                if self.for_delete(row, instance):
                    if new:
                        row_result.import_type = RowResult.IMPORT_TYPE_SKIP
                        row_result.diff = self.get_diff(None, None,
                                real_dry_run)
                    else:
                        row_result.import_type = RowResult.IMPORT_TYPE_DELETE
                        self.delete_instance(instance, real_dry_run)
                        row_result.diff = self.get_diff(original, None,
                                real_dry_run)
                else:
                    self.import_obj(instance, row)
                    self.save_instance(instance, real_dry_run)
                    self.save_m2m(instance, row, real_dry_run)
                    row_result.diff = self.get_diff(original, instance,
                            real_dry_run)
            except Exception, e:
                tb_info = traceback.format_exc(sys.exc_info()[2])
                row_result.errors.append(Error(repr(e), tb_info))
                if raise_errors:
                    if use_transactions:
                        transaction.rollback()
                        transaction.leave_transaction_management()
                    raise
            result.rows.append(row_result)

        if use_transactions:
            if dry_run or result.has_errors():
                transaction.rollback()
            else:
                transaction.commit()
            transaction.leave_transaction_management()

        return result

    def get_export_order(self):
        return self._meta.export_order or self.fields.keys()

    def export_field(self, field, obj):
        method = getattr(self, 'dehydrate_%s' % field.column_name, None)
        if method is not None:
            return method(obj)
        return field.export(obj)

    def export_resource(self, obj):
        return [self.export_field(field, obj) for field in self.get_fields()]

    def get_export_headers(self):
        headers = [field.column_name for field in self.get_fields()]
        return headers

    def export(self, queryset=None):
        if queryset is None:
            queryset = self.get_queryset()
        headers = self.get_export_headers()
        data = tablib.Dataset(headers=headers)
        for obj in queryset:
            data.append(self.export_resource(obj))
        return data


class ModelDeclarativeMetaclass(DeclarativeMetaclass):

    def __new__(cls, name, bases, attrs):
        new_class = super(ModelDeclarativeMetaclass,
                cls).__new__(cls, name, bases, attrs)

        opts = new_class._meta

        if not opts.instance_loader_class:
            opts.instance_loader_class = ModelInstanceLoader

        if opts.model:
            model_opts = opts.model._meta
            declared_fields = new_class.fields

            field_list = []
            for f in sorted(model_opts.fields + model_opts.many_to_many):
                if opts.fields is not None and not f.name in opts.fields:
                    continue
                if opts.exclude and f.name in opts.exclude:
                    continue
                if f.name in declared_fields:
                    continue

                FieldWidget = new_class.widget_from_django_field(f)
                widget_kwargs = new_class.widget_kwargs_for_field(f.name)
                field = Field(attribute=f.name, column_name=f.name,
                        widget=FieldWidget(**widget_kwargs))
                field_list.append((f.name, field, ))

            new_class.fields.update(SortedDict(field_list))

            #add fields that follow relationships
            if opts.fields is not None:
                field_list = []
                for field_name in opts.fields:
                    if field_name in declared_fields:
                        continue
                    if field_name.find('__') == -1:
                        continue

                    model = opts.model
                    attrs = field_name.split('__')
                    for attr in attrs[0:-1]:
                        f = model._meta.get_field_by_name(attr)[0]
                        model = f.rel.to
                    f = model._meta.get_field_by_name(attrs[-1])[0]
                    if isinstance(f, RelatedObject):
                        f = f.field

                    FieldWidget = new_class.widget_from_django_field(f)
                    widget_kwargs = new_class.widget_kwargs_for_field(field_name)
                    field = Field(attribute=field_name, column_name=field_name,
                            widget=FieldWidget(**widget_kwargs), readonly=True)
                    field_list.append((field_name, field, ))

                new_class.fields.update(SortedDict(field_list))

        return new_class


class ModelResource(Resource):
    """
    ModelResource is Resource subclass for handling Django models.
    """
    __metaclass__ = ModelDeclarativeMetaclass

    @classmethod
    def widget_from_django_field(cls, f, default=widgets.Widget):
        """
        Returns the widget that would likely be associated with each
        Django type.
        """
        result = default
        internal_type = f.get_internal_type()
        if internal_type in ('ManyToManyField', ):
            result = functools.partial(widgets.ManyToManyWidget,
                    model=f.rel.to)
        if internal_type in ('ForeignKey', 'OneToOneField', ):
            result = functools.partial(widgets.ForeignKeyWidget,
                    model=f.rel.to)
        if internal_type in ('DecimalField', ):
            result = widgets.DecimalWidget
        if internal_type in ('DateTimeField', ):
            result = widgets.DateTimeWidget
        elif internal_type in ('DateField', ):
            result = widgets.DateWidget
        elif internal_type in ('IntegerField', 'PositiveIntegerField',
                'PositiveSmallIntegerField', 'SmallIntegerField', 'AutoField'):
            result = widgets.IntegerWidget
        elif internal_type in ('BooleanField', 'NullBooleanField'):
            result = widgets.BooleanWidget
        return result

    @classmethod
    def widget_kwargs_for_field(self, field_name):
        """
        Returns widget kwargs for given field_name.
        """
        if self._meta.widgets:
            return self._meta.widgets.get(field_name, {})
        return {}

    def get_import_id_fields(self):
        return self._meta.import_id_fields

    def get_queryset(self):
        return self._meta.model.objects.all()

    def init_instance(self, row=None):
        return self._meta.model()


def modelresource_factory(model, resource_class=ModelResource):
    """
    Factory for creating ``ModelResource`` class for given Django model.
    """
    attrs = {'model': model}
    Meta = type('Meta', (object,), attrs)

    class_name = model.__name__ + 'Resource'

    class_attrs = {
        'Meta': Meta,
        }

    metaclass = ModelDeclarativeMetaclass
    return metaclass(class_name, (resource_class,), class_attrs)
