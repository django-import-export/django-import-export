from unittest import TestCase

import django
from core.models import WithPositiveIntegerFields
from django.contrib.contenttypes import fields as contenttype_fields
from django.contrib.postgres import fields as postgres
from django.contrib.postgres import search as postgres_search
from django.contrib.postgres.fields import ranges as postgres_ranges
from django.db import models
from django.db.models.fields.related import ForeignKey, RelatedField

from import_export import widgets
from import_export.resources import ModelResource
from import_export.widgets import ForeignKeyWidget


class ExampleResource(ModelResource):
    class Meta:
        model = WithPositiveIntegerFields


class TestFieldWidgetMapping(TestCase):
    def test_field_has_correct_widget(self):
        resource = ExampleResource()
        with self.subTest("PositiveBigIntegerField"):
            self.assertIsInstance(resource.fields["big"].widget, widgets.IntegerWidget)
        with self.subTest("PositiveSmallIntegerField"):
            self.assertIsInstance(
                resource.fields["small"].widget,
                widgets.IntegerWidget,
            )

    def test_all_db_fields_has_widgets(self):
        all_django_fields_classes = self._get_all_django_model_field_subclasses()
        expected_has_default_widget = self._get_fields_with_expected_default_widget()
        expected_not_presented_fields = (
            self._get_expected_not_presented_in_test_field_subclasses()
        )
        all_fields = self._get_django_fields_for_check_widget()

        field_instance_by_field_cls = {field.__class__: field for field in all_fields}

        for field_cls, field in field_instance_by_field_cls.items():
            with self.subTest(msg=field_cls.__name__):
                resource_field = ModelResource.field_from_django_field(
                    "test", field, False
                )
                widget = resource_field.widget
                if field_cls in expected_has_default_widget:
                    self.assertEqual(
                        widget.__class__,
                        widgets.Widget,
                        msg=(
                            f"{field_cls.__name__} "
                            "expected default widget "
                            f"actual {widget.__class__}"
                        ),
                    )
                else:
                    self.assertNotEqual(
                        widget.__class__,
                        widgets.Widget,
                        msg=f"{field_cls.__name__} has default widget class",
                    )

        # if in new version django will be added new field subclass
        # this subtest should fail
        for field_cls in all_django_fields_classes:
            if field_cls in expected_not_presented_fields:
                continue
            with self.subTest(msg=field_cls.__name__):
                self.assertIn(
                    field_cls,
                    field_instance_by_field_cls,
                    msg=f"{field_cls.__name__} not presented in test fields",
                )

    def _get_fields_with_expected_default_widget(self):
        """
        Returns set of django.db.models.field.Field subclasses
        which expected has default Widget in ModelResource
        """
        expected_has_default_widget = {
            models.BinaryField,
            models.FileField,
            models.FilePathField,
            models.GenericIPAddressField,
            models.ImageField,
            models.IPAddressField,
            models.TextField,
            models.UUIDField,
            postgres.BigIntegerRangeField,
            postgres.CITextField,
            postgres.DateRangeField,
            postgres.DateTimeRangeField,
            postgres.DecimalRangeField,
            postgres.HStoreField,
            postgres.IntegerRangeField,
            postgres.RangeField,
        }
        return expected_has_default_widget

    def _get_expected_not_presented_in_test_field_subclasses(self):
        """
        Return set of django.db.models.field.Field subclasses
        which expected NOT presented in this test in
         _get_django_fields_for_check_widget
        """
        expected_not_presented_fields = {
            contenttype_fields.GenericRelation,
            models.ForeignObject,
            postgres_search.SearchQueryField,
            postgres_search.SearchVectorField,
            RelatedField,
            postgres_ranges.ContinuousRangeField,
            postgres_search._Float4Field,
        }
        if django.VERSION >= (5, 0):
            expected_not_presented_fields |= {models.GeneratedField}
        if django.VERSION >= (5, 1):
            expected_not_presented_fields |= {contenttype_fields.GenericForeignKey}
        if django.VERSION >= (5, 2):
            expected_not_presented_fields |= {models.CompositePrimaryKey}
        return expected_not_presented_fields

    def _get_all_django_model_field_subclasses(self):
        """
        returns list of classes - all subclasses for django.db.models.field.Field
        """
        return self._collect_all_clas_children(models.Field)

    def _collect_all_clas_children(self, clas):
        children = []
        for child_clas in clas.__subclasses__():
            children.append(child_clas)
            children.extend(self._collect_all_clas_children(child_clas))
        return children

    def _get_django_fields_for_check_widget(self):
        """
        Return list of field instances for all checking field classes
        """
        fields = [
            models.AutoField(),
            models.BigAutoField(),
            models.BigIntegerField(),
            models.BinaryField(),
            models.BooleanField(),
            models.CharField(),
            models.CommaSeparatedIntegerField(),
            models.DateField(),
            models.DateTimeField(),
            models.DecimalField(),
            models.DurationField(),
            models.EmailField(),
            models.FileField(),
            models.FilePathField(),
            models.FloatField(),
            models.ForeignKey(WithPositiveIntegerFields, on_delete=models.PROTECT),
            models.GenericIPAddressField(),
            models.ImageField(),
            models.IntegerField(),
            models.IPAddressField(),
            models.JSONField(),
            models.ManyToManyField(WithPositiveIntegerFields),
            models.NullBooleanField(),
            models.OneToOneField(WithPositiveIntegerFields, on_delete=models.PROTECT),
            models.OrderWrt(),
            models.PositiveBigIntegerField(),
            models.PositiveIntegerField(),
            models.PositiveSmallIntegerField(),
            models.SlugField(),
            models.SmallAutoField(),
            models.SmallIntegerField(),
            models.TextField(),
            models.TimeField(),
            models.URLField(),
            models.UUIDField(),
            postgres.ArrayField(models.CharField),
            postgres.BigIntegerRangeField(),
            postgres.CICharField(),
            postgres.CIEmailField(),
            postgres.CITextField(),
            postgres.DateRangeField(),
            postgres.DateTimeRangeField(),
            postgres.DecimalRangeField(),
            postgres.HStoreField(),
            postgres.IntegerRangeField(),
            postgres.JSONField(),
            postgres.RangeField(),
        ]
        return fields

    def test_custom_fk_field(self):
        # issue 1817 - if a 'custom' foreign key field is provided, then this should
        # be handled when widgets are defined
        class CustomForeignKey(ForeignKey):
            def __init__(
                self,
                to,
                on_delete,
                **kwargs,
            ):
                super().__init__(to, on_delete, **kwargs)

        resource_field = ModelResource.field_from_django_field(
            "custom_fk",
            CustomForeignKey(WithPositiveIntegerFields, on_delete=models.SET_NULL),
            False,
        )
        self.assertEqual(ForeignKeyWidget, resource_field.widget.__class__)
