# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from decimal import Decimal
from datetime import datetime, date
from django.utils import datetime_safe, timezone, six
from django.utils.encoding import smart_text, force_text
from django.utils.dateparse import parse_duration
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
import json
import ast


class Widget(object):
    """
    A Widget takes care of converting between import and export representations.

    This is achieved by the two methods,
    :meth:`~import_export.widgets.Widget.clean` and
    :meth:`~import_export.widgets.Widget.render`.
    """
    def clean(self, value, row=None, *args, **kwargs):
        """
        Returns an appropriate Python object for an imported value.

        For example, if you import a value from a spreadsheet,
        :meth:`~import_export.widgets.Widget.clean` handles conversion
        of this value into the corresponding Python object.

        Numbers or dates can be *cleaned* to their respective data types and
        don't have to be imported as Strings.
        """
        return value

    def render(self, value, obj=None):
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
        if isinstance(value, six.string_types):
            value = value.strip()
        # 0 is not empty
        return value is None or value == ""

    def render(self, value, obj=None):
        return value


class FloatWidget(NumberWidget):
    """
    Widget for converting floats fields.
    """

    def clean(self, value, row=None, *args, **kwargs):
        if self.is_empty(value):
            return None
        return float(value)


class IntegerWidget(NumberWidget):
    """
    Widget for converting integer fields.
    """

    def clean(self, value, row=None, *args, **kwargs):
        if self.is_empty(value):
            return None
        return int(float(value))


class DecimalWidget(NumberWidget):
    """
    Widget for converting decimal fields.
    """

    def clean(self, value, row=None, *args, **kwargs):
        if self.is_empty(value):
            return None
        return Decimal(value)


class CharWidget(Widget):
    """
    Widget for converting text fields.
    """

    def render(self, value, obj=None):
        return force_text(value)


class BooleanWidget(Widget):
    """
    Widget for converting boolean fields.
    """
    TRUE_VALUES = ["1", 1]
    FALSE_VALUE = "0"

    def render(self, value, obj=None):
        if value is None:
            return ""
        return self.TRUE_VALUES[0] if value else self.FALSE_VALUE

    def clean(self, value, row=None, *args, **kwargs):
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

    def clean(self, value, row=None, *args, **kwargs):
        if not value:
            return None
        if isinstance(value, date):
            return value
        for format in self.formats:
            try:
                return datetime.strptime(value, format).date()
            except (ValueError, TypeError):
                continue
        raise ValueError("Enter a valid date.")

    def render(self, value, obj=None):
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

    def clean(self, value, row=None, *args, **kwargs):
        if not value:
            return None
        if isinstance(value, datetime):
            return value
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

    def render(self, value, obj=None):
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

    def clean(self, value, row=None, *args, **kwargs):
        if not value:
            return None
        for format in self.formats:
            try:
                return datetime.strptime(value, format).time()
            except (ValueError, TypeError):
                continue
        raise ValueError("Enter a valid time.")

    def render(self, value, obj=None):
        if not value:
            return ""
        return value.strftime(self.formats[0])


class DurationWidget(Widget):
    """
    Widget for converting time duration fields.
    """

    def clean(self, value, row=None, *args, **kwargs):
        if not value:
            return None

        try:
            return parse_duration(value)
        except (ValueError, TypeError):
            raise ValueError("Enter a valid duration.")

    def render(self, value, obj=None):
        if not value:
            return ""
        return str(value)


class SimpleArrayWidget(Widget):
    def __init__(self, separator=None):
        if separator is None:
            separator = ','
        self.separator = separator
        super(SimpleArrayWidget, self).__init__()

    def clean(self, value, row=None, *args, **kwargs):
        return value.split(self.separator) if value else []

    def render(self, value, obj=None):
        return self.separator.join(six.text_type(v) for v in value)


class JSONWidget(Widget):
    """
    Widget for a JSON object (especially required for jsonb fields in PostgreSQL database.)
    """

    def clean(self, value, row=None, *args, **kwargs):
        val = super(JSONWidget, self).clean(value)
        if val:
            return ast.literal_eval(val)

    def render(self, value, obj=None):
        if value:
            return json.dumps(value)


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

        from import_export import fields, resources
        from import_export.widgets import ForeignKeyWidget

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

    def get_queryset(self, value, row, *args, **kwargs):
        """
        Returns a queryset of all objects for this Model.

        Overwrite this method if you want to limit the pool of objects from
        which the related object is retrieved.

        :param value: The field's value in the datasource.
        :param row: The datasource's current row.

        As an example; if you'd like to have ForeignKeyWidget look up a Person
        by their pre- **and** lastname column, you could subclass the widget
        like so::

            class FullNameForeignKeyWidget(ForeignKeyWidget):
                def get_queryset(self, value, row):
                    return self.model.objects.filter(
                        first_name__iexact=row["first_name"],
                        last_name__iexact=row["last_name"]
                    )
        """
        return self.model.objects.all()

    def clean(self, value, row=None, *args, **kwargs):
        val = super(ForeignKeyWidget, self).clean(value)
        if val:
            return self.get_queryset(value, row, *args, **kwargs).get(**{self.field: val})
        else:
            return None

    def render(self, value, obj=None):
        if value is None:
            return ""

        attrs = self.field.split('__')
        for attr in attrs:
            try:
                value = getattr(value, attr, None)
            except (ValueError, ObjectDoesNotExist):
                # needs to have a primary key value before a many-to-many
                # relationship can be used.
                return None
            if value is None:
                return None

        return value


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

    def clean(self, value, row=None, *args, **kwargs):
        if not value:
            return self.model.objects.none()
        if isinstance(value, (float, int)):
            ids = [int(value)]
        else:
            ids = value.split(self.separator)
            ids = filter(None, [i.strip() for i in ids])
        return self.model.objects.filter(**{
            '%s__in' % self.field: ids
        })

    def render(self, value, obj=None):
        ids = [smart_text(getattr(obj, self.field)) for obj in value.all()]
        return self.separator.join(ids)
