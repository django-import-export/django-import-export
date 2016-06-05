from __future__ import unicode_literals

from . import widgets

from django.core.exceptions import ObjectDoesNotExist
from django.db.models.manager import Manager
from django.db.models.fields import NOT_PROVIDED


class Field(object):
    """
    Field represent mapping between `object` field and representation of
    this field.

    :param attribute: A string of either an instance attribute or callable off
        the object.

    :param column_name: Lets you provide a name for the column that represents
        this field in the export.

    :param widget: Defines a widget that will be used to represent this
        field's data in the export.

    :param readonly: A Boolean which defines if this field will be ignored
        during import.

    :param default: This value will be returned by
        :meth:`~import_export.fields.Field.clean` if this field's widget did
        not return an adequate value.
    """
    empty_values = [None, '']

    def __init__(self, attribute=None, column_name=None, widget=None,
                 default=NOT_PROVIDED, readonly=False):
        self.attribute = attribute
        self.default = default
        self.column_name = column_name
        if not widget:
            widget = widgets.Widget()
        self.widget = widget
        self.readonly = readonly

    def __repr__(self):
        """
        Displays the module, class and name of the field.
        """
        path = '%s.%s' % (self.__class__.__module__, self.__class__.__name__)
        column_name = getattr(self, 'column_name', None)
        if column_name is not None:
            return '<%s: %s>' % (path, column_name)
        return '<%s>' % path

    def clean(self, data):
        """
        Translates the value stored in the imported datasource to an
        appropriate Python object and returns it.
        """
        try:
            value = data[self.column_name]
        except KeyError:
            raise KeyError("Column '%s' not found in dataset. Available "
                           "columns are: %s" % (self.column_name,
                                                list(data.keys())))

        try:
            value = self.widget.clean(value)
        except ValueError as e:
            raise ValueError("Column '%s': %s" % (self.column_name, e))

        if value in self.empty_values and self.default != NOT_PROVIDED:
            if callable(self.default):
                return self.default()
            return self.default

        return value

    def get_value(self, obj):
        """
        Returns the value of the object's attribute.
        """
        if self.attribute is None:
            return None

        attrs = self.attribute.split('__')
        value = obj

        for attr in attrs:
            try:
                value = getattr(value, attr, None)
            except (ValueError, ObjectDoesNotExist):
                # needs to have a primary key value before a many-to-many
                # relationship can be used.
                return None
            if value is None:
                return None

        # RelatedManager and ManyRelatedManager classes are callable in
        # Django >= 1.7 but we don't want to call them
        if callable(value) and not isinstance(value, Manager):
            value = value()
        return value

    def save(self, obj, data):
        """
        If this field is not declared readonly, the object's attribute will
        be set to the value returned by :meth:`~import_export.fields.Field.clean`.
        """
        if not self.readonly:
            attrs = self.attribute.split('__')
            for attr in attrs[:-1]:
                obj = getattr(obj, attr, None)
            setattr(obj, attrs[-1], self.clean(data))

    def export(self, obj):
        """
        Returns value from the provided object converted to export
        representation.
        """
        value = self.get_value(obj)
        if value is None:
            return ""
        return self.widget.render(value)


class CombinedField(Field):
    def __init__(self, model, mapping, *args, **kwargs):
        self.model = model
        self.mapping = mapping
        super().__init__(*args, **kwargs)

    def clean(self, data):
        search = {}
        for csvfield, modelfield in self.mapping.items():
            search[modelfield] = data.get(csvfield)
        return self.model.objects.get(**search)


class CachedCombinedField(Field):
    """
    class PropertyImportResource(resources.ModelResource):
        client = CachedCombinedField(
            column_name='client',
            attribute='client',
            model=Client,
            mapping={
                # { csv field name: client model field name }
                'client': 'name',
                'primary_contact': 'primary_contact',
            },
    )
    """
    cached_instances = None

    def __init__(self, model, mapping, *args, **kwargs):
        self.model = model
        self.mapping = mapping # { csv row heading => client model field name }
        self.cache_keys = self.mapping.keys() # Do this once, order is important and not guarenteed otherwise
        super().__init__(*args, **kwargs)

    def build_cache(self, cache_keys, mapping):
        cache = {}
        # this will look like:
        # cache[("Vic Body Corp Serv", "Manager #1")]
        for row in self.model.objects.all():
            key = ()
            for csv_field_name in cache_keys:
                model_field_name = mapping[csv_field_name]
                key = key + (getattr(row, model_field_name), )
            cache[key] = row
        return cache

    def clean(self, data):
        # Build the cache if it doesn't exist
        if not self.cached_instances:
            self.cached_instances = self.build_cache(self.cache_keys, self.mapping)

        # Grab the CSV values in the correct order
        key = ()
        for csv_field_name in self.cache_keys:
            value = data.get(csv_field_name)
            key = key + (self.widget.clean(value), )

        obj = self.cached_instances.get(key, False)

        # Build a nice error message
        if not obj:
            search = [self.mapping[csv_field_name] for csv_field_name in self.cache_keys]
            raise ValueError('{model} not found matching {search} = {values}'.format(
                model=self.model.__name__,
                search=tuple(search),
                values=key
            ))

        return obj
