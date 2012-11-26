import widgets


class Field(object):
    """
    The base implementation of a field.
    """

    def __init__(self, attribute=None, column_name=None, widget=None):
        """
        ``attribute`` string of either an instance attribute or callable
        off the object.

        ``column_name`` let you provide how this field is named
        in datasource.

        ``widget`` defines widget that will be used to represent field data
        in export.
        """
        self.attribute = attribute
        self.column_name = column_name
        if not widget:
            widget = widgets.Widget()
        self.widget = widget

    def __repr__(self):
        """
        Displays the module, class and name of the field.
        """
        path = '%s.%s' % (self.__class__.__module__, self.__class__.__name__)
        column_name = getattr(self, 'column_name', None)
        if column_name is not None:
            return '<%s: %s>' % (path, column_name)
        return '<%s>' % path

    def convert(self, value):
        """
        Handles conversion between the data found and the type of the field.

        Extending classes should override this method and provide correct
        data coercion.
        """
        return self.widget.render(value)

    def clean(self, data):
        """
        Takes data stored in the data for the field and returns it as
        appropriate python object.
        """
        value = data[self.column_name]
        value = self.widget.clean(value)
        return value

    def get_value(self, obj):
        """
        Return value of object.
        """
        if self.attribute is None:
            return None
        value = getattr(obj, self.attribute)
        if callable(value):
            value = value()
        return value

    def export(self, obj):
        """
        Takes data from the provided object and prepares it for export.
        """
        value = self.get_value(obj)
        if value is None:
            return ""
        return self.convert(value)


class DateField(Field):

    def __init__(self, *args, **kwargs):
        widget = kwargs.get('widget') or widgets.DateWidget()
        kwargs['widget'] = widget
        super(DateField, self).__init__(*args, **kwargs)


class IntegerField(Field):

    def __init__(self, *args, **kwargs):
        widget = kwargs.get('widget') or widgets.IntegerWidget()
        kwargs['widget'] = widget
        super(IntegerField, self).__init__(*args, **kwargs)


class BooleanField(Field):

    def __init__(self, *args, **kwargs):
        widget = kwargs.get('widget') or widgets.BooleanWidget()
        kwargs['widget'] = widget
        super(BooleanField, self).__init__(*args, **kwargs)
