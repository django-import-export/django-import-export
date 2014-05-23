from __future__ import unicode_literals

from . import widgets

from django.core.exceptions import ObjectDoesNotExist
from django.db.models.fields import FieldDoesNotExist


class Field(object):
    """
    Field represent mapping between `object` field and representation of
    this field.

    ``attribute`` string of either an instance attribute or callable
    off the object.

    ``column_name`` let you provide how this field is named
    in datasource.

    ``db_column`` string of column name in DB backend. Used to get value of
    foreign key fields without loading related instance.

    ``widget`` defines widget that will be used to represent field data
    in export.

    ``readonly`` boolean value defines that if this field will be assigned
    to object during import.
    """

    def __init__(self, attribute=None, column_name=None, db_column=None,
                 widget=None, readonly=False):
        self.attribute = attribute
        self.column_name = column_name
        self.db_column = db_column
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

    def clean(self, data, obj):
        """
        Takes value stored in the data for the field and returns it as
        appropriate python object.
        """
        value = data[self.column_name]
        value = self.widget.clean(value)

        try:
            field = obj._meta.get_field(self.attribute)
            value = field.clean(value, obj)
        except (TypeError, AttributeError, FieldDoesNotExist), e:
            # dealing with something not a model field of model instance
            pass

        return value

    def _get_attrs(self):
        # Use DB column name if possible to avoid expensive
        # DB lookups on FK fields
        if '__' in self.attribute:  # highest priority
            return self.attribute.split('__')
        if self.db_column:  # important for FKs
            return [self.db_column]
        return [self.attribute]  # default behaviour

    def get_value(self, obj):
        """
        Returns value for this field from object attribute.
        """
        if self.attribute is None:
            return None

        attrs = self._get_attrs()
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
            setattr(obj, self.db_column or self.attribute,
                    self.clean(data, obj))

    def export(self, obj):
        """
        Returns value from the provided object converted to export
        representation.
        """
        value = self.get_value(obj)
        if value is None:
            return ""
        return self.widget.render(value)
