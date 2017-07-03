from __future__ import unicode_literals

from decimal import Decimal
from django.contrib.contenttypes.models import ContentType
from django.utils import translation
from faker.providers import currency
from parler.utils.context import switch_language

from core.loading import get_model
from . import widgets

from django.core.exceptions import ObjectDoesNotExist
from django.db.models.manager import Manager
from django.db.models.fields import NOT_PROVIDED

Price = get_model('pricing', 'Price')
""" :type:  core.pricing.models.Price"""
Currency = get_model('pricing', 'Currency')
""" :type:  core.pricing.models.Currency"""
TaxRatio = get_model('pricing', 'TaxRatio')
""" :type:  core.pricing.models.TaxRatio"""
AttributeOptionGroupValue = get_model('catalog', 'AttributeOptionGroupValue')
""" :type:  core.catalog.models.AttributeOptionGroupValue"""
AttributeOptionGroup = get_model('catalog', 'AttributeOptionGroup')
""" :type:  core.catalog.models.AttributeOptionGroup"""
AttributeOption = get_model('catalog', 'AttributeOption')
""" :type:  core.catalog.models.AttributeOption"""

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


class TranslatableField(Field):
    def get_value(self, obj):

        if self.attribute is None:
            return None

        tmp = self.attribute.split('_')
        attr_name = "_".join(tmp[:-1])
        attr_language = tmp[-1]

        value = obj
        with switch_language(value, attr_language):
            translation.activate(attr_language)

            try:
                value = getattr(value, attr_name, None)
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
            tmp = self.attribute.split('_')
            attr_name = "_".join(tmp[:-1])
            attr_language = tmp[-1]
            with switch_language(obj, attr_language):
                translation.activate(attr_language)
                field = obj._meta.model.translations.field.model._meta.get_field(attr_name)
                if field.blank and not field.null and not field.is_relation:
                    if self.clean(data) is None:
                        setattr(obj, attr_name, '')
                    else:
                        setattr(obj, attr_name, self.clean(data))
                else:
                    setattr(obj, attr_name, self.clean(data))


class PriceField(Field):
    def get_value(self, obj):

        if self.attribute is None:
            return None

        tmp = self.attribute.split('_')
        attr_currency = tmp[-1]
        attr_tax_ratio = tmp[-2]

        try:
            price_obj = obj.prices.get(currency__code=attr_currency, tax_ratio__percentage=attr_tax_ratio)
            value = price_obj.price_excluding_tax
        except (ValueError, ObjectDoesNotExist):
            return None

        return value

    def save(self, obj, data):
        """
        If this field is not declared readonly, the object's attribute will
        be set to the value returned by :meth:`~import_export.fields.Field.clean`.
        """
        if not self.readonly:
            tmp = self.attribute.split('_')
            attr_name = "_".join(tmp[:-4])
            attr_currency = tmp[-1]
            attr_tax_ratio = tmp[-2]
            attr_tax_ratio = Decimal(attr_tax_ratio)
            value = self.clean(data)

            if value is '' or value is None:
                return
            else:
                value = Decimal(value)
                related_object_type = ContentType.objects.get_for_model(obj)
                # if not dry_run:
                obj.save()
                price, created = Price.objects.update_or_create(
                    content_type_id=related_object_type.id,
                    object_id=obj.id,
                    currency=Currency.objects.get(code=attr_currency),
                    tax_ratio=TaxRatio.objects.get(percentage=attr_tax_ratio),
                    defaults={attr_name: value}
                )

                # else:
                # Price(content_type_id=related_object_type.id,
                #     object_id=obj.id,
                #     currency=Currency.objects.get(code=attr_currency),
                #     tax_ratio=TaxRatio.objects.get(percentage=attr_tax_ratio),
                #       **{attr_name: value})


class AttributeField(Field):
    def get_value(self, obj):

        if self.attribute is None:
            return None

        tmp = self.attribute.split('_')
        attr_type = "_".join(tmp[1:])

        try:
            att_value = obj.option_values.get(group__name=attr_type)
        except (ValueError, ObjectDoesNotExist):
            return None

        return att_value.value.name

    def save(self, obj, data):
        """
        If this field is not declared readonly, the object's attribute will
        be set to the value returned by :meth:`~import_export.fields.Field.clean`.
        """
        if not self.readonly:
            tmp = self.attribute.split('_')
            attr_type = "_".join(tmp[1:])
            value = self.clean(data)

            if value is '' or value is None:
                return
            else:
                obj.save()
                attr, created = AttributeOptionGroupValue.objects.update_or_create(
                    product=obj,
                    group=AttributeOptionGroup.objects.get(name=attr_type),
                    value=AttributeOption.objects.get(name=value),
                )

