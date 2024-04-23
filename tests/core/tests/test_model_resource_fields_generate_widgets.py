from unittest import TestCase

import django
from django.contrib.postgres import fields as postgres_fields
from django.db import models

from import_export import widgets
from import_export.resources import ModelResource

from ..models import WithPositiveIntegerFields


class ExampleResource(ModelResource):
    class Meta:
        model = WithPositiveIntegerFields


class TestImportExportBug(TestCase):
    def test_field_has_correct_widget(self):
        resource = ExampleResource()
        with self.subTest("PositiveBigIntegerField"):
            self.assertIsInstance(resource.fields["big"], widgets.IntegerWidget)
        with self.subTest("PositiveSmallIntegerField"):
            self.assertIsInstance(resource.fields["small"], widgets.IntegerWidget)

    def test_all_db_fields_has_widgets(self):
        all_django_fields_classes = self._collect_all_clas_children(models.Field)
        expected_not_presented_fields = {
            models.ForeignObject,
            models.ImageField,
            models.FileField,
            models.BinaryField,
            models.FilePathField,
        }
        if django.VERSION >= (5, 0):
            expected_not_presented_fields |= {models.GeneratedField}
        all_fields = (
            self._get_default_django_fields() + self._get_postgres_django_fields()
        )

        field_instance_by_field_cls = {field.__class__: field for field in all_fields}

        for field_cls, field in field_instance_by_field_cls.items():
            with self.subTest(msg=field_cls.__name__):
                resource_field = ModelResource.field_from_django_field(
                    "test", field, False
                )
                widget = resource_field.widget
                self.assertNotEqual(
                    widget.__class__.__name__,
                    "Widget",
                    msg=f"{field_cls.__name__} has default widget",
                )

        for field_cls in all_django_fields_classes:
            if field_cls in expected_not_presented_fields:
                continue
            with self.subTest(msg=field_cls.__name__):
                self.assertIn(
                    field_cls,
                    field_instance_by_field_cls,
                    msg=f"{field_cls.__name__} not presented in test widgets",
                )

    def _collect_all_clas_children(self, cls):
        children = []
        for child_cls in cls.__subclasses__():
            children.append(child_cls)
            children.extend(self._collect_all_clas_children(child_cls))
        return children

    def _get_default_django_fields(self):
        fields = [
            models.PositiveBigIntegerField(),
            models.PositiveSmallIntegerField(),
            models.ManyToManyField(WithPositiveIntegerFields),
            models.OneToOneField(WithPositiveIntegerFields, on_delete=models.PROTECT),
            models.ForeignKey(WithPositiveIntegerFields, on_delete=models.PROTECT),
            models.JSONField(),
            models.UUIDField(),
            models.TimeField(),
            models.TextField(),
            models.GenericIPAddressField(),
            models.IPAddressField(),
            models.OrderWrt(),
            models.AutoField(),
            models.PositiveIntegerField(),
            models.SmallAutoField(),
            models.PositiveSmallIntegerField(),
            models.SmallIntegerField(),
            models.BigAutoField(),
            models.PositiveBigIntegerField(),
            models.BigIntegerField(),
            models.IntegerField(),
            models.FloatField(),
            models.DurationField(),
            models.DecimalField(),
            models.DateTimeField(),
            models.DateField(),
            models.URLField(),
            models.SlugField(),
            models.EmailField(),
            models.CommaSeparatedIntegerField(),
            models.CharField(),
            models.NullBooleanField(),
            models.BooleanField(),
        ]
        return fields

    def _get_postgres_django_fields(self):
        return [
            postgres_fields.DateRangeField(),
            postgres_fields.BigIntegerRangeField(),
            postgres_fields.IntegerRangeField(),
            postgres_fields.DateTimeRangeField(),
            postgres_fields.DecimalRangeField(),
            postgres_fields.RangeField(),
            postgres_fields.HStoreField(),
            postgres_fields.ArrayField(models.CharField),
            postgres_fields.CITextField(),
            postgres_fields.CICharField(),
            postgres_fields.CIEmailField(),
        ]
