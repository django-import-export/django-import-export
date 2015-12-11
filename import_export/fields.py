from __future__ import unicode_literals

from . import widgets

from django.core.exceptions import ObjectDoesNotExist
from django.db.models.manager import Manager
from django.db.models.fields import NOT_PROVIDED


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

    ``default`` value returned by :meth`clean` if returned value evaluates to
    False
    """

    def __init__(self, attribute=None, column_name=None, widget=None,
                 default=None, readonly=False):
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
        Takes value stored in the data for the field and returns it as
        appropriate python object.
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

        if not value and self.default != NOT_PROVIDED:
            if callable(self.default):
                return self.default()

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
        Cleans this field value and assign it to provided object.
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
