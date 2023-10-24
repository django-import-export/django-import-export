import json
import logging
from datetime import date, datetime, time
from decimal import Decimal

import django
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from django.utils.dateparse import parse_duration
from django.utils.encoding import force_str, smart_str
from django.utils.formats import number_format
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)


def format_datetime(value, datetime_format):
    # conditional logic to handle correct formatting of dates
    # see https://code.djangoproject.com/ticket/32738
    if django.VERSION[0] >= 4:
        format = django.utils.formats.sanitize_strftime_format(datetime_format)
        return value.strftime(format)
    else:
        return django.utils.datetime_safe.new_datetime(value).strftime(datetime_format)


class Widget:
    """
    A Widget takes care of converting between import and export representations.

    This is achieved by the two methods,
    :meth:`~import_export.widgets.Widget.clean` and
    :meth:`~import_export.widgets.Widget.render`.
    """

    def clean(self, value, row=None, **kwargs):
        """
        Returns an appropriate Python object for an imported value.

        For example, if you import a value from a spreadsheet,
        :meth:`~import_export.widgets.Widget.clean` handles conversion
        of this value into the corresponding Python object.

        Numbers or dates can be *cleaned* to their respective data types and
        don't have to be imported as Strings.

        Implementations may raise
        `ValueError <https://docs.python.org/3/library/exceptions.html#ValueError/>`_.
        with a suitable message to indicate that a value could not be transformed
        successfully.
        """
        return value

    def render(self, value, obj=None):
        """
        Returns an export representation of a Python value.

        For example, if you have an object you want to export,
        :meth:`~import_export.widgets.Widget.render` takes care of converting
        the object's field to a value that can be written to a spreadsheet.
        """
        return force_str(value)


class NumberWidget(Widget):
    """
    Widget for converting numeric fields.

    :param coerce_to_string: If True, render will return a string representation
        of the value (None is returned as ""), otherwise the value is returned.
    """

    def __init__(self, coerce_to_string=False):
        self.coerce_to_string = coerce_to_string

    def is_empty(self, value):
        if isinstance(value, str):
            value = value.strip()
        # 0 is not empty
        return value is None or value == ""

    def render(self, value, obj=None):
        if self.coerce_to_string:
            return "" if value is None else number_format(value)
        return value


class FloatWidget(NumberWidget):
    """
    Widget for converting float fields.
    """

    def clean(self, value, row=None, **kwargs):
        if self.is_empty(value):
            return None
        return float(value)


class IntegerWidget(NumberWidget):
    """
    Widget for converting integer fields.
    """

    def clean(self, value, row=None, **kwargs):
        if self.is_empty(value):
            return None
        return int(Decimal(value))


class DecimalWidget(NumberWidget):
    """
    Widget for converting decimal fields.
    """

    def clean(self, value, row=None, **kwargs):
        if self.is_empty(value):
            return None
        return Decimal(force_str(value))


class CharWidget(Widget):
    """
    Widget for converting text fields.

    :param coerce_to_string: If True, the value returned by clean() is cast to a
      string.
    :param allow_blank:  If True, and if coerce_to_string is True, then clean() will
      return null values as empty strings, otherwise as null.
    """

    def __init__(self, coerce_to_string=False, allow_blank=False):
        """ """
        self.coerce_to_string = coerce_to_string
        self.allow_blank = allow_blank

    def clean(self, value, row=None, **kwargs):
        val = super().clean(value, row, **kwargs)
        if self.coerce_to_string is True:
            if val is None:
                if self.allow_blank is True:
                    return ""
            else:
                return force_str(val)
        return val


class BooleanWidget(Widget):
    """
    Widget for converting boolean fields.

    The widget assumes that ``True``, ``False``, and ``None`` are all valid
    values, as to match Django's `BooleanField
    <https://docs.djangoproject.com/en/dev/ref/models/fields/#booleanfield>`_.
    That said, whether the database/Django will actually accept NULL values
    will depend on if you have set ``null=True`` on that Django field.

    While the BooleanWidget is set up to accept as input common variations of
    "True" and "False" (and "None"), you may need to munge less common values
    to ``True``/``False``/``None``. Probably the easiest way to do this is to
    override the :func:`~import_export.resources.Resource.before_import_row`
    function of your Resource class. A short example::

        from import_export import fields, resources, widgets

        class BooleanExample(resources.ModelResource):
            warn = fields.Field(widget=widgets.BooleanWidget())

            def before_import_row(self, row, row_number=None, **kwargs):
                if "warn" in row.keys():
                    # munge "warn" to "True"
                    if row["warn"] in ["warn", "WARN"]:
                        row["warn"] = True

                return super().before_import_row(row, row_number, **kwargs)
    """

    TRUE_VALUES = ["1", 1, True, "true", "TRUE", "True"]
    FALSE_VALUES = ["0", 0, False, "false", "FALSE", "False"]
    NULL_VALUES = ["", None, "null", "NULL", "none", "NONE", "None"]

    def render(self, value, obj=None):
        """
        On export, ``True`` is represented as ``1``, ``False`` as ``0``, and
        ``None``/NULL as a empty string.

        Note that these values are also used on the import confirmation view.
        """
        if value in self.NULL_VALUES:
            return ""
        return self.TRUE_VALUES[0] if value else self.FALSE_VALUES[0]

    def clean(self, value, row=None, **kwargs):
        if value in self.NULL_VALUES:
            return None
        return True if value in self.TRUE_VALUES else False


class DateWidget(Widget):
    """
    Widget for converting date fields.

    Takes optional ``format`` parameter. If none is set, either
    ``settings.DATE_INPUT_FORMATS`` or ``"%Y-%m-%d"`` is used.
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

    def clean(self, value, row=None, **kwargs):
        """
        :returns: A python date instance.
        :raises: ValueError if the value cannot be parsed using defined formats.
        """
        if not value:
            return None
        if isinstance(value, date):
            return value
        for format in self.formats:
            try:
                return datetime.strptime(value, format).date()
            except (ValueError, TypeError) as e:
                logger.debug(str(e))
        raise ValueError(_("Value could not be parsed using defined date formats."))

    def render(self, value, obj=None):
        if not value:
            return ""
        return format_datetime(value, self.formats[0])


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

    def clean(self, value, row=None, **kwargs):
        """
        :returns: A python datetime instance.
        :raises: ValueError if the value cannot be parsed using defined formats.
        """
        dt = None
        if not value:
            return None
        if isinstance(value, datetime):
            dt = value
        else:
            for format_ in self.formats:
                try:
                    dt = datetime.strptime(value, format_)
                except (ValueError, TypeError) as e:
                    logger.debug(str(e))
        if dt:
            if settings.USE_TZ and timezone.is_naive(dt):
                dt = timezone.make_aware(dt)
            return dt
        raise ValueError(_("Value could not be parsed using defined datetime formats."))

    def render(self, value, obj=None):
        if not value:
            return ""
        if settings.USE_TZ:
            value = timezone.localtime(value)
        return format_datetime(value, self.formats[0])


class TimeWidget(Widget):
    """
    Widget for converting time fields.

    Takes optional ``format`` parameter. If none is set, either
    ``settings.DATETIME_INPUT_FORMATS`` or ``"%H:%M:%S"`` is used.
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

    def clean(self, value, row=None, **kwargs):
        """
        :returns: A python time instance.
        :raises: ValueError if the value cannot be parsed using defined formats.
        """
        if not value:
            return None
        if isinstance(value, time):
            return value
        for format in self.formats:
            try:
                return datetime.strptime(value, format).time()
            except (ValueError, TypeError) as e:
                logger.debug(str(e))
        raise ValueError(_("Value could not be parsed using defined time formats."))

    def render(self, value, obj=None):
        if not value:
            return ""
        return value.strftime(self.formats[0])


class DurationWidget(Widget):
    """
    Widget for converting time duration fields.
    """

    def clean(self, value, row=None, **kwargs):
        """
        :returns: A python duration instance.
        :raises: ValueError if the value cannot be parsed.
        """
        if not value:
            return None

        try:
            return parse_duration(value)
        except (ValueError, TypeError) as e:
            logger.debug(str(e))
            raise ValueError(_("Value could not be parsed."))

    def render(self, value, obj=None):
        if value is None:
            return ""
        return str(value)


class SimpleArrayWidget(Widget):
    """
    Widget for an Array field. Can be used for Postgres' Array field.

    :param separator: Defaults to ``','``
    """

    def __init__(self, separator=None):
        if separator is None:
            separator = ","
        self.separator = separator
        super().__init__()

    def clean(self, value, row=None, **kwargs):
        return value.split(self.separator) if value else []

    def render(self, value, obj=None):
        return self.separator.join(str(v) for v in value)


class JSONWidget(Widget):
    """
    Widget for a JSON object
    (especially required for jsonb fields in PostgreSQL database.)

    :param value: Defaults to JSON format.
    The widget covers two cases: Proper JSON string with double quotes, else it
    tries to use single quotes and then convert it to proper JSON.
    """

    def clean(self, value, row=None, **kwargs):
        val = super().clean(value)
        if val:
            try:
                return json.loads(val)
            except json.decoder.JSONDecodeError:
                return json.loads(val.replace("'", '"'))

    def render(self, value, obj=None):
        if value:
            return json.dumps(value)


class ForeignKeyWidget(Widget):
    """
    Widget for a ``ForeignKey`` field which looks up a related model using
    either the PK or a user specified field that uniquely identifies the
    instance in both export and import.

    The lookup field defaults to using the primary key (``pk``) as lookup
    criterion but can be customized to use any field on the related model.

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
    :param field: A field on the related model used for looking up a particular
        object.
    :param use_natural_foreign_keys: Use natural key functions to identify
        related object, default to False
    """

    def __init__(self, model, field="pk", use_natural_foreign_keys=False, **kwargs):
        self.model = model
        self.field = field
        self.use_natural_foreign_keys = use_natural_foreign_keys
        super().__init__(**kwargs)

    def get_queryset(self, value, row, *args, **kwargs):
        """
        Returns a queryset of all objects for this Model.

        Overwrite this method if you want to limit the pool of objects from
        which the related object is retrieved.

        :param value: The field's value in the dataset.
        :param row: The dataset's current row.
        :param \\*args:
            Optional args.
        :param \\**kwargs:
            Optional kwargs.

        As an example; if you'd like to have ForeignKeyWidget look up a Person
        by their pre- **and** lastname column, you could subclass the widget
        like so::

            class FullNameForeignKeyWidget(ForeignKeyWidget):
                def get_queryset(self, value, row, *args, **kwargs):
                    return self.model.objects.filter(
                        first_name__iexact=row["first_name"],
                        last_name__iexact=row["last_name"]
                    )
        """
        return self.model.objects.all()

    def clean(self, value, row=None, **kwargs):
        """
        Return a single Foreign Key instance derived from the args.
        ``None`` can be returned if the value passed is a null value.

        :param value: The field's value in the dataset.
        :param row: The dataset's current row.
        :param \\**kwargs:
            Optional kwargs.
        :raises: ``ObjectDoesNotExist`` if no valid instance can be found.
        """
        val = super().clean(value)
        if val:
            if self.use_natural_foreign_keys:
                # natural keys will always be a tuple, which ends up as a json list.
                value = json.loads(value)
                return self.model.objects.get_by_natural_key(*value)
            else:
                lookup_kwargs = self.get_lookup_kwargs(value, row, **kwargs)
                return self.get_queryset(value, row, **kwargs).get(**lookup_kwargs)
        else:
            return None

    def get_lookup_kwargs(self, value, row, **kwargs):
        """
        Returns the key value pairs used to identify a model instance.
        Override this to customize instance look up.

        :param value: The field's value in the dataset.
        :param row: The dataset's current row.
        :param \\**kwargs:
            Optional kwargs.
        """
        return {self.field: value}

    def render(self, value, obj=None):
        if value is None:
            return ""

        attrs = self.field.split("__")
        for attr in attrs:
            try:
                if self.use_natural_foreign_keys:
                    # inbound natural keys must be a json list.
                    return json.dumps(value.natural_key())
                else:
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

    def __init__(self, model, separator=None, field=None, **kwargs):
        if separator is None:
            separator = ","
        if field is None:
            field = "pk"
        self.model = model
        self.separator = separator
        self.field = field
        super().__init__(**kwargs)

    def clean(self, value, row=None, **kwargs):
        if not value:
            return self.model.objects.none()
        if isinstance(value, (float, int)):
            ids = [int(value)]
        else:
            ids = value.split(self.separator)
            ids = filter(None, [i.strip() for i in ids])
        return self.model.objects.filter(**{"%s__in" % self.field: ids})

    def render(self, value, obj=None):
        ids = [smart_str(getattr(obj, self.field)) for obj in value.all()]
        return self.separator.join(ids)
