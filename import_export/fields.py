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
            value = self.widget.clean(value, row=data)
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
        return self.widget.render(value, obj)


class ResourceField(Field):

    """Proxy to the resource class

    Support method on resource without writing field

    .. code-block:: python

        class MyModelResource(ModelReource):

            def export_myextra_field(self, obj):

                return obj.related.value

            def save_myextra_field(self, obj, data):
                # optional

                RelatedObject.create(**data)
                RelatedObject1.create(**data)

            def get_myextra_field_name(self):
                # optional

                return "ColumnName"

    """

    def __init__(self, column_name, resource, id=None, *args, **kwargs):

        self.resource = resource

        super(ResourceField, self).__init__(
            column_name=column_name,
            *args, **kwargs)

        self.attribute = column_name

        method = getattr(resource, 'get_%s_name' % column_name, None)

        if method:
            self.column_name = method()
        else:
            self.column_name = column_name

        self.id = column_name

        if not hasattr(self.resource,
                       "export_%s" % self.attribute):
            raise NotImplementedError("Missing export method for "
                                      "declared field %s" % self.attribute)

        if not hasattr(resource, "save_%s" % self.attribute):
            self.readonly = True

    def save(self, obj, data):
        """
        Call save method field on resource
        """

        if not self.readonly:
            method = getattr(self.resource,
                             "save_%s" % self.attribute,
                             None)

            method(obj, data)

    def get_value(self, obj):
        """
        Returns the value of the object's attribute.

        def export_fieldname(self, obj):
            return obj.whatever

        """

        method = getattr(self.resource,
                         "export_%s" % self.attribute,
                         None)

        return method(obj)
