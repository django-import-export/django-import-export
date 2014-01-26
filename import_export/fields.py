from __future__ import unicode_literals

from . import widgets

from django.core.exceptions import ObjectDoesNotExist


class Field(object):
    """
    Field represent mapping between `object` field and representation of
    this field.

    ``attribute`` string of either an instance attribute or callable
    off the object.

    ``column_name`` let you provide how this field is named
    in datasource.

    ``widget`` defines widget that will be used to represent field data
    in export.

    ``readonly`` boolean value defines that if this field will be assigned
    to object during import.
    """

    def __init__(self, attribute=None, column_name=None, widget=None,
            readonly=False):
        self.attribute = attribute
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
        Takes value stored in the data for the field and returns it as
        appropriate python object.
        """
        value = data[self.column_name]
        value = self.widget.clean(value)
        return value

    def get_value(self, obj):
        """
        Returns value for this field from object attribute.
        """
        if self.attribute is None:
            return None

        attrs = self.attribute.split('__')
        value = obj

        for attr in attrs:
            try:
                value = getattr(value, attr)
            except (ValueError, ObjectDoesNotExist):
                # needs to have a primary key value before a many-to-many
                # relationship can be used.
                return None
            if value is None:
                return None

        if callable(value):
            value = value()
        return value

    def save(self, obj, data):
        """
        Cleans this field value and assign it to provided object.
        """
        if not self.readonly:
            setattr(obj, self.attribute, self.clean(data))

    def export(self, obj):
        """
        Returns value from the provided object converted to export
        representation.
        """
        value = self.get_value(obj)
        if value is None:
            return ""
        return self.widget.render(value)
