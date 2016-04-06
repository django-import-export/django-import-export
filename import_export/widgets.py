# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from decimal import Decimal
from datetime import datetime
from django.utils import datetime_safe, timezone
from django.utils.encoding import smart_text
from django.conf import settings

try:
    from django.utils.encoding import force_text
except ImportError:
    from django.utils.encoding import force_unicode as force_text


class Widget(object):
    """
    A Widget takes care of converting between import and export representations.

    This is achieved by the two methods,
    :meth:`~import_export.widgets.Widget.clean` and
    :meth:`~import_export.widgets.Widget.render`.
    """

    def clean(self, value):
        """
        Returns an appropriate Python object for an imported value.

        For example, if you import a value from a spreadsheet,
        :meth:`~import_export.widgets.Widget.clean` handles conversion
        of this value into the corresponding Python object.

        Numbers or dates can be *cleaned* to their respective data types and
        don't have to be imported as Strings.
        """
        return value

    def render(self, value):
        """
        Returns an export representation of a Python value.

        For example, if you have an object you want to export,
        :meth:`~import_export.widgets.Widget.render` takes care of converting
        the object's field to a value that can be written to a spreadsheet.
        """
        return force_text(value)


class NumberWidget(Widget):
    """
    """

    def is_empty(self, value):
        # 0 is not empty
        return value is None or value == ""

    def render(self, value):
        return value


class FloatWidget(NumberWidget):
    """
    Widget for converting floats fields.
    """

    def clean(self, value):
        if self.is_empty(value):
            return None
        return float(value)


class IntegerWidget(NumberWidget):
    """
    Widget for converting integer fields.
    """

    def clean(self, value):
        if self.is_empty(value):
            return None
        return int(float(value))


class DecimalWidget(NumberWidget):
    """
    Widget for converting decimal fields.
    """

    def clean(self, value):
        if self.is_empty(value):
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

    Takes optional ``format`` parameter. If none is set, either
    ``settings.DATETIME_INPUT_FORMATS`` or ``"%Y-%m-%d %H:%M:%S"`` is used.
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
                dt = datetime.strptime(value, format)
                if settings.USE_TZ:
                    # make datetime timezone aware so we don't compare
                    # naive datetime to an aware one
                    dt = timezone.make_aware(dt,
                                             timezone.get_default_timezone())
                return dt
            except (ValueError, TypeError):
                continue
        raise ValueError("Enter a valid date/time.")

    def render(self, value):
        if not value:
            return ""
        return value.strftime(self.formats[0])


class TimeWidget(Widget):
    """
    Widget for converting time fields.

    Takes optional ``format`` parameter.
    """

    def __init__(self, format=None):
        if format is None:
            if not settings.TIME_INPUT_FORMATS:
                formats = ("%H:%M:%S",)
            else:
                formats = settings.TIME_INPUT_FORMATS
        else:
            formats = (format,)
        self.formats = formats

    def clean(self, value):
        if not value:
            return None
        for format in self.formats:
            try:
                return datetime.strptime(value, format).time()
            except (ValueError, TypeError):
                continue
        raise ValueError("Enter a valid time.")

    def render(self, value):
        if not value:
            return ""
        return value.strftime(self.formats[0])


class ForeignKeyWidget(Widget):
    """
    Widget for a ``ForeignKey`` field which looks up a related model using
    "natural keys" in both export an import.

    The lookup field defaults to using the primary key (``pk``) as lookup
    criterion but can be customised to use any field on the related model.

    Unlike specifying a related field in your resource like so…

    ::

        class Meta:
            fields = ('author__name',)

    …using a :class:`~import_export.widgets.ForeignKeyWidget` has the
    advantage that it can not only be used for exporting, but also importing
    data with foreign key relationships.

    Here's an example on how to use
    :class:`~import_export.widgets.ForeignKeyWidget` to lookup related objects
    using ``Author.name`` instead of ``Author.pk``::

        class BookResource(resources.ModelResource):
            author = fields.Field(
                column_name='author',
                attribute='author',
                widget=ForeignKeyWidget(Author, 'name'))

            class Meta:
                fields = ('author',)

    :param model: The Model the ForeignKey refers to (required).
    :param field: A field on the related model used for looking up a particular object.
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
    Widget that converts between representations of a ManyToMany relationships
    as a list and an actual ManyToMany field.

    :param model: The model the ManyToMany field refers to (required).
    :param separator: Defaults to ``','``.
    :param field: A field on the related model. Default is ``pk``.
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
        if isinstance(value, float):
            ids = [int(value)]
        else:
            ids = value.split(self.separator)
        ids = filter(None, value.split(self.separator))
        return self.model.objects.filter(**{
            '%s__in' % self.field: ids
        })

    def render(self, value):
        ids = [smart_text(getattr(obj, self.field)) for obj in value.all()]
        return self.separator.join(ids)
