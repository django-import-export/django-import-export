from datetime import datetime


class Widget(object):
    """
    """
    def clean(self, value):
        """
        Returns appropriate python objects for value.
        """
        return value

    def render(self, value):
        """
        Returns render representation of python value.
        """
        return unicode(value)


class IntegerWidget(Widget):

    def clean(self, value):
        if not value:
            return None
        return int(value)


class CharWidget(Widget):

    def render(self, value):
        return unicode(value)


class BooleanWidget(Widget):
    TRUE_VALUE = "1"
    FALSE_VALUE = "0"

    def render(self, value):
        return self.TRUE_VALUE if value else self.FALSE_VALUE

    def clean(self, value):
        return True if value == self.TRUE_VALUE else False


class DateWidget(Widget):

    def __init__(self, format=None):
        if format is None:
            format = "%Y-%m-%d"
        self.format = format

    def clean(self, value):
        if not value:
            return None
        return datetime.strptime(value, self.format).date()

    def render(self, value):
        return value.strftime(self.format)
