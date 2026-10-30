import os.path
from collections.abc import Iterable
from copy import deepcopy
from itertools import chain

from django import forms
from django.conf import settings
from django.core.exceptions import (
    FieldDoesNotExist,
    ImproperlyConfigured,
    ValidationError,
)
from django.db import connections
from django.db.models import ForeignObject, IntegerField, QuerySet
from django.utils.translation import gettext_lazy as _

from . import constants
from .constants import FORM_FIELD_PREFIX
from .resources import ModelResource


class FieldNamePrefixMixin:
    """
    Handles adding a constant to form field names so that there are
    no name clashes with model field names.
    """

    field_name_mapping = {
        key: f"{constants.FORM_FIELD_PREFIX}{key}"
        for key in ["format", "resource", "export_items"]
    }

    def add_prefix(self, field_name):
        # look up field name; return original if not found
        field_name = self.field_name_mapping.get(field_name, field_name)
        return super().add_prefix(field_name)


class ImportExportFormBase(FieldNamePrefixMixin, forms.Form):
    # id attr is explicitly declared because js logic uses the id
    resource = forms.ChoiceField(
        label=_("Resource"),
        choices=(),
        required=False,
        widget=forms.Select(attrs={"id": "id_resource"}),
    )
    format = forms.ChoiceField(
        label=_("Format"),
        choices=(),
    )

    def __init__(self, formats, resources, **kwargs):
        super().__init__(**kwargs)
        self._init_resources(resources)
        self._init_formats(formats)

    def _init_resources(self, resources):
        if not resources:
            raise ValueError("no defined resources")
        self.fields["resource"].choices = [
            (i, resource.get_display_name()) for i, resource in enumerate(resources)
        ]
        if len(resources) == 1:
            self.fields["resource"].widget = forms.HiddenInput(
                attrs={"id": "id_resource"}
            )
            self.initial["resource"] = "0"

    def _init_formats(self, formats):
        if not formats:
            raise ValueError("invalid formats list")

        choices = [(str(i), f().get_title()) for i, f in enumerate(formats)]
        if len(formats) == 1:
            field = self.fields["format"]
            field.value = formats[0]().get_title()
            field.initial = 0
            field.widget.attrs["readonly"] = True
        if len(formats) > 1:
            choices.insert(0, ("", "---"))

        self.fields["format"].choices = choices


class ImportForm(ImportExportFormBase):
    import_file = forms.FileField(label=_("File to import"))

    # field ordered for usability:
    # ensure that the 'file' select appears before 'format'
    # so that the 'guess_format' js logic makes sense
    field_order = ["resource", "import_file", "format"]

    def __init__(self, formats, resources, **kwargs):
        super().__init__(formats, resources, **kwargs)
        if len(formats) > 1:
            self.fields["import_file"].widget.attrs["class"] = "guess_format"
            self.fields["format"].widget.attrs["class"] = "guess_format"

    @property
    def media(self):
        media = super().media
        extra = "" if settings.DEBUG else ".min"
        return media + forms.Media(
            js=(
                f"admin/js/vendor/jquery/jquery{extra}.js",
                "admin/js/jquery.init.js",
                "import_export/guess_format.js",
            )
        )


class ConfirmImportForm(FieldNamePrefixMixin, forms.Form):
    import_file_name = forms.CharField(widget=forms.HiddenInput())
    original_file_name = forms.CharField(widget=forms.HiddenInput())
    format = forms.CharField(widget=forms.HiddenInput())
    resource = forms.CharField(widget=forms.HiddenInput(), required=False)

    def clean_import_file_name(self):
        data = self.cleaned_data["import_file_name"]
        data = os.path.basename(data)
        return data


class ExportItemsField(forms.ModelMultipleChoiceField):
    """
    ``export_items`` field, validated against the posted pks only.

    Without a queryset, a non-empty selection raises ``ImproperlyConfigured``
    and an empty one returns ``[]``, or fails ``required`` when the field is
    required.  With a queryset, ``clean()`` returns an
    unevaluated ``QuerySet`` of the selected rows.  Values outside the range of
    an integer key field are rejected with the ``invalid_choice`` error.

    ``to_field_name`` must name a unique field: every row sharing a selected
    value is exported.

    The admin sets this field's queryset after the form's ``__init__()``, and
    adds the field to a form that has none when exporting selected items, so a
    queryset declared on the field or set in ``__init__()`` is replaced.
    Narrow the selection in ``get_export_queryset()`` or
    ``clean_export_items()`` instead.
    """

    def clean(self, value):
        if self.queryset is None:
            if value:
                raise ImproperlyConfigured(
                    "export_items requires a QuerySet: in the admin, "
                    "get_export_queryset() must return a QuerySet to export "
                    "selected items; otherwise pass queryset= when "
                    "instantiating the export form, and from a custom "
                    "__init__() to super().__init__()."
                )
            if self.required:
                raise ValidationError(self.error_messages["required"], code="required")
            return []
        return super().clean(value)

    def _check_values(self, value):
        # Django's ModelMultipleChoiceField._check_values (>= 6.0), except
        # that it reads only the key column, returns the queryset unevaluated
        # and leaves _out_of_range() values out of the IN list.
        key = self.to_field_name or "pk"
        try:
            value = frozenset(value)
        except TypeError:
            raise ValidationError(
                self.error_messages["invalid_list"],
                code="invalid_list",
            )
        for pk in value:
            self.validate_no_null_characters(pk)
            try:
                self.queryset.filter(**{key: pk})
            except (ValueError, TypeError, ValidationError):
                raise ValidationError(
                    self.error_messages["invalid_pk_value"],
                    code="invalid_pk_value",
                    params={"pk": pk},
                )
        in_range = value - self._out_of_range(value)
        qs = self.queryset.filter(**{"%s__in" % key: in_range})
        pks = {str(pk) for pk in qs.values_list(key, flat=True)}
        for val in value:
            if str(val) not in pks:
                raise ValidationError(
                    self.error_messages["invalid_choice"],
                    code="invalid_choice",
                    params={"value": val},
                )
        return qs

    def _out_of_range(self, value):
        # Django's ``In`` lookup has no integer overflow guard (unlike exact,
        # gt, lt...), so out of range values would raise OverflowError on
        # SQLite.
        opts = self.queryset.model._meta
        if (self.to_field_name or "pk") == "pk":
            range_field = opts.pk
        else:
            try:
                range_field = opts.get_field(self.to_field_name)
            except FieldDoesNotExist:
                # e.g. an annotation
                return set()
        while isinstance(range_field, ForeignObject):
            range_field = range_field.target_field
        if not isinstance(range_field, IntegerField):
            return set()
        ops = connections[self.queryset.db].ops
        try:
            min_value, max_value = ops.integer_field_range(
                range_field.get_internal_type()
            )
        except KeyError:
            # custom get_internal_type(): the backend knows no range for it
            return set()
        out_of_range = set()
        for pk in value:
            try:
                pk_int = int(pk)
            except (ValueError, TypeError):
                continue
            if (min_value is not None and pk_int < min_value) or (
                max_value is not None and pk_int > max_value
            ):
                out_of_range.add(pk)
        return out_of_range

    @classmethod
    def check_field(cls, field):
        if not isinstance(field, cls):
            raise ImproperlyConfigured(
                "export_items must be an ExportItemsField: redeclare it as "
                "import_export.forms.ExportItemsField or a subclass."
            )


class ExportForm(ImportExportFormBase):
    """
    Pass ``queryset`` to validate selected ``export_items`` when the form is
    used outside the admin, which binds the field's queryset itself.  Without
    it, validating a non-empty selection raises ``ImproperlyConfigured``.
    """

    export_items = ExportItemsField(
        queryset=None, widget=forms.MultipleHiddenInput(), required=False
    )

    def __init__(self, formats, resources, *, queryset=None, **kwargs):
        super().__init__(formats, resources, **kwargs)
        field = self.fields.get("export_items")
        if queryset is not None and field is not None:
            ExportItemsField.check_field(field)
            if not isinstance(queryset, QuerySet):
                raise ImproperlyConfigured(
                    "ExportForm queryset= must be a QuerySet to validate "
                    f"export_items, not {type(queryset).__name__}."
                )
            field.queryset = queryset


class SelectableFieldsExportForm(ExportForm):
    """
    :class:`ExportForm` with a checkbox per resource field.  It accepts the
    same ``queryset`` argument.
    """

    def __init__(self, formats, resources, **kwargs):
        super().__init__(formats, resources, **kwargs)
        self._init_selectable_fields(resources)

    @property
    def media(self):
        media = super().media
        return media + forms.Media(
            js=("import_export/export_selectable_fields.js",),
            css={
                "all": ["import_export/export.css"],
            },
        )

    def _init_selectable_fields(self, resources: Iterable[ModelResource]) -> None:
        """
        Create `BooleanField(s)` for resource fields
        """
        self.resources = resources
        self.is_selectable_fields_form = True
        self.resource_fields = {resource.__name__: [] for resource in resources}

        for index, resource in enumerate(resources):
            boolean_fields = self._create_boolean_fields(resource, index)
            self.resource_fields[resource.__name__] = boolean_fields

        # Order fields by resource select then boolean fields
        ordered_fields = [
            "resource",
            # flatten resource fields lists
            *chain(*self.resource_fields.values()),
        ]
        self.order_fields(ordered_fields)

    def _get_field_label(self, resource: ModelResource, field_name: str) -> str:
        title = field_name.replace("_", " ").title()
        field = resource.fields.get(field_name)
        if field and field.column_name != field_name:
            title = f"{title} ({field.column_name})"
        return title

    def _create_boolean_fields(self, resource: ModelResource, index: int) -> None:
        # Initiate resource to get export fields (respects overridden get_export_fields)
        resource_instance = resource()

        # Check if get_export_fields() has been overridden
        # (not using default implementation) by comparing the class hierarchy
        export_fields_method = resource_instance.__class__.get_export_fields
        from import_export.resources import Resource

        is_overridden = export_fields_method != Resource.get_export_fields

        if is_overridden:
            # Use get_export_fields() when it's been overridden
            export_fields = resource_instance.get_export_fields()
            # Find the field names (keys) that correspond to these Field objects
            fields = []
            for export_field in export_fields:
                for field_name, field_obj in resource_instance.fields.items():
                    if field_obj is export_field:
                        fields.append(field_name)
                        break
        else:
            # Fall back to get_export_order() for backward compatibility
            # when get_export_fields() is not overridden
            fields = resource_instance.get_export_order()
        boolean_fields = []  # will be used for ordering the fields
        is_initial_field = False

        for field in fields:
            field_name = self.create_boolean_field_name(resource, field)
            boolean_field = forms.BooleanField(
                label=self._get_field_label(resource, field),
                label_suffix="",
                initial=True,
                required=False,
            )

            # These attributes will be used for rendering in template
            boolean_field.is_selectable_field = True
            boolean_field.resource_name = resource.__name__
            boolean_field.resource_index = index
            boolean_field.widget.attrs["resource-id"] = index
            if is_initial_field is False:
                boolean_field.initial_field = is_initial_field = True

            self.fields[field_name] = boolean_field
            boolean_fields.append(field_name)

        return boolean_fields

    @staticmethod
    def create_boolean_field_name(resource: ModelResource, field_name: str) -> str:
        """
        Create field name by combining `resource_name` + `field_name` to prevent
        conflict between resource fields with same name

        Example:
            BookResource            +   name -> bookresource_name
            BookResourceWithNames   +   name -> bookresourcewithnames_name
        """
        return resource.__name__.lower() + "_" + field_name

    def clean(self):
        selected_resource = self.get_selected_resource()

        if selected_resource:
            # Remove fields for not selected resources
            self._remove_unselected_resource_fields(selected_resource)
            # Normalize resource field names
            self._normalize_resource_fields(selected_resource)
            # Validate at least one field is selected for selected resource
            self._validate_any_field_selected(selected_resource)

        return self.cleaned_data

    def _remove_unselected_resource_fields(
        self, selected_resource: ModelResource
    ) -> None:
        """
        Remove boolean fields except the fields for selected resource
        """
        _cleaned_data = deepcopy(self.cleaned_data)

        for resource_name, fields in self.resource_fields.items():
            if selected_resource.__name__ == resource_name:
                # Skip selected resource
                continue

            for field in fields:
                del _cleaned_data[field]

        self.cleaned_data = _cleaned_data

    def get_selected_resource(self):
        if not getattr(self, "cleaned_data", None):
            raise forms.ValidationError(
                _("Form is not validated, call `is_valid` first")
            )

        # Return selected resource by index
        resource_index = 0
        if f"{FORM_FIELD_PREFIX}resource" in self.data:
            try:
                resource_index = int(self.data[f"{FORM_FIELD_PREFIX}resource"])
            except ValueError:
                pass
        return self.resources[resource_index]

    def _normalize_resource_fields(self, selected_resource: ModelResource) -> None:
        """
        Field names are combination of resource_name + field_name,
        normalize field names by removing resource name
        """
        selected_resource_name = selected_resource.__name__.lower() + "_"
        _cleaned_data = {}
        self._selected_resource_fields = []

        for k, v in self.cleaned_data.items():
            if selected_resource_name in k:
                field_name = k.replace(selected_resource_name, "")
                _cleaned_data[field_name] = v
                if v is True:
                    # Add to _selected_resource_fields to determine what
                    # fields were selected for export
                    self._selected_resource_fields.append(field_name)
                continue
            _cleaned_data[k] = v

        self.cleaned_data = _cleaned_data

    def get_selected_resource_export_fields(self):
        selected_resource = self.get_selected_resource()
        # Initialize resource to use `get_export_order` method
        resource_fields = selected_resource().get_export_order()
        return [
            field
            for field, value in self.cleaned_data.items()
            if value is True and field in resource_fields
        ]

    def _validate_any_field_selected(self, resource) -> None:
        """
        Validate if any field for resource was selected in form data
        """
        resource_fields = list(resource().get_export_order())

        if not any(v for k, v in self.cleaned_data.items() if k in resource_fields):
            raise forms.ValidationError(
                _("""Select at least 1 field for "%(resource_name)s" to export"""),
                code="invalid",
                params={
                    "resource_name": resource.get_display_name(),
                },
            )
