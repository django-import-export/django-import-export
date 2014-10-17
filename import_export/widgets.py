from __future__ import unicode_literals

from decimal import Decimal
from datetime import datetime
from django.utils import datetime_safe
from django.utils.encoding import smart_text
from django.conf import settings

try:
    from django.utils.encoding import force_text
except ImportError:
    from django.utils.encoding import force_unicode as force_text


class Widget(object):
    """
    Widget takes care of converting between import and export representations.

    Widget objects have two functions:

    * converts object field value to export representation

    * converts import value and converts it to appropriate python
      representation
    """
    def clean(self, value):
        """
        Returns appropriate python objects for import value.
        """
        return value

    def render(self, value):
        """
        Returns export representation of python value.
        """
        return force_text(value)


class NumberWidget(Widget):

    def render(self, value):
        return value


class IntegerWidget(NumberWidget):
    """
    Widget for converting integer fields.
    """

    def clean(self, value):
        if not value and value is not 0:
            return None
        return int(value)


class DecimalWidget(NumberWidget):
    """
    Widget for converting decimal fields.
    """

    def clean(self, value):
        if not value:
            return None
        return Decimal(value)


class CharWidget(Widget):
    """
    Widget for converting text fields.
    """

    def render(self, value):
        return force_text(value)


class BooleanWidget(Widget):
    """
    Widget for converting boolean fields.
    """
    TRUE_VALUES = ["1", 1]
    FALSE_VALUE = "0"

    def render(self, value):
        if value is None:
            return ""
        return self.TRUE_VALUES[0] if value else self.FALSE_VALUE

    def clean(self, value):
        if value == "":
            return None
        return True if value in self.TRUE_VALUES else False


class DateWidget(Widget):
    """
    Widget for converting date fields.

    Takes optional ``format`` parameter.
    """

    def __init__(self, format=None):
        if format is None:
            if not settings.DATE_INPUT_FORMATS:
                formats = ("%Y-%m-%d",)
            else:
                formats = settings.DATE_INPUT_FORMATS
        else:
            formats = (format,)
        self.formats = formats

    def clean(self, value):
        if not value:
            return None
        for format in self.formats:
            try:
                return datetime.strptime(value, format).date()
            except (ValueError, TypeError):
                continue
        raise ValueError("Enter a valid date.")

    def render(self, value):
        if not value:
            return ""
        try:
            return value.strftime(self.formats[0])
        except:
            return datetime_safe.new_date(value).strftime(self.formats[0])


class DateTimeWidget(Widget):
    """
    Widget for converting date fields.

    Takes optional ``format`` parameter.
    """

    def __init__(self, format=None):
        if format is None:
            if not settings.DATETIME_INPUT_FORMATS:
                formats = ("%Y-%m-%d %H:%M:%S",)
            else:
                formats = settings.DATETIME_INPUT_FORMATS
        else:
            formats = (format,)
        self.formats = formats

    def clean(self, value):
        if not value:
            return None
        for format in self.formats:
            try:
                return datetime.strptime(value, format)
            except (ValueError, TypeError):
                continue
        raise ValueError("Enter a valid date/time.")

    def render(self, value):
        if not value:
            return ""
        return value.strftime(self.formats[0])


class ForeignKeyWidget(Widget):
    """
    Widget for ``ForeignKey`` which looks up a related model.

    The lookup field defaults to using the primary key (``pk``), but
    can be customised to use any field on the related model.

    e.g. To use a lookup field other than ``pk``, rather than specifying a
    field in your Resource as ``class Meta: fields = ('author__name', ...)``,
    you would specify it in your Resource like so:

        class BookResource(resources.ModelResource):
            author = fields.Field(column_name='author', attribute='author', \
                widget=ForeignKeyWidget(Author, 'name'))
            class Meta: fields = ('author', ...)

    This will allow you to use "natural keys" for both import and export.

    Parameters:
        ``model`` should be the Model instance for this ForeignKey (required).
        ``field`` should be the lookup field on the related model.
    """
    def __init__(self, model, field='pk', *args, **kwargs):
        self.model = model
        self.field = field
        super(ForeignKeyWidget, self).__init__(*args, **kwargs)

    def clean(self, value):
        val = super(ForeignKeyWidget, self).clean(value)
        return self.model.objects.get(**{self.field: val}) if val else None

    def render(self, value):
        if value is None:
            return ""
        return getattr(value, self.field)


class ManyToManyWidget(Widget):
    """
    Widget for ``ManyToManyField`` model field that represent m2m field
    as values that identify many-to-many relationship.

    Requires a positional argument: the class to which the field is related.

    Optional keyword arguments are:

        separator - default ","

        field - field of related model, default ``pk``
    """

    def __init__(self, model, separator=None, field=None, *args, **kwargs):
        if separator is None:
            separator = ','
        if field is None:
            field = 'pk'
        self.model = model
        self.separator = separator
        self.field = field
        super(ManyToManyWidget, self).__init__(*args, **kwargs)

    def clean(self, value):
        if not value:
            return self.model.objects.none()
        ids = value.split(self.separator)
        return self.model.objects.filter(**{
            '%s__in' % self.field: ids
        })

    def render(self, value):
        ids = [smart_text(getattr(obj, self.field)) for obj in value.all()]
        return self.separator.join(ids)
