import logging
from warnings import warn

from django.conf import settings
from django.http import HttpResponse
from django.utils.timezone import now
from django.views.generic.edit import FormView

from .formats import base_formats
from .forms import SelectableFieldsExportForm
from .resources import modelresource_factory
from .signals import post_export

logger = logging.getLogger(__name__)


class BaseImportExportMixin:
    resource_classes = []

    @property
    def formats(self):
        return getattr(settings, "IMPORT_EXPORT_FORMATS", base_formats.DEFAULT_FORMATS)

    @property
    def export_formats(self):
        return getattr(settings, "EXPORT_FORMATS", self.formats)

    @property
    def import_formats(self):
        return getattr(settings, "IMPORT_FORMATS", self.formats)

    def check_resource_classes(self, resource_classes):
        if resource_classes and not hasattr(resource_classes, "__getitem__"):
            raise Exception(
                "The resource_classes field type must be "
                "subscriptable (list, tuple, ...)"
            )

    def get_resource_classes(self):
        """Return subscriptable type (list, tuple, ...) containing resource classes"""
        if not self.resource_classes:
            return [modelresource_factory(self.model)]
        return self.resource_classes

    def get_resource_kwargs(self, request, *args, **kwargs):
        return {}

    def get_resource_index(self, form):
        resource_index = 0
        if form and "resource" in form.cleaned_data:
            try:
                resource_index = int(form.cleaned_data["resource"])
            except ValueError:
                pass
        return resource_index


class BaseImportMixin(BaseImportExportMixin):
    def get_import_resource_classes(self):
        """
        Returns ResourceClass subscriptable (list, tuple, ...) to use for import.
        """
        resource_classes = self.get_resource_classes()
        self.check_resource_classes(resource_classes)
        return resource_classes

    def get_import_formats(self):
        """
        Returns available import formats.
        """
        return [f for f in self.import_formats if f().can_import()]

    def get_import_resource_kwargs(self, request, **kwargs):
        return self.get_resource_kwargs(request, **kwargs)

    def choose_import_resource_class(self, form):
        resource_index = self.get_resource_index(form)
        return self.get_import_resource_classes()[resource_index]


class BaseExportMixin(BaseImportExportMixin):
    model = None

    def get_export_formats(self):
        """
        Returns available export formats.
        """
        return [f for f in self.export_formats if f().can_export()]

    def get_export_resource_classes(self):
        """
        Returns ResourceClass subscriptable (list, tuple, ...) to use for export.
        """
        resource_classes = self.get_resource_classes()
        self.check_resource_classes(resource_classes)
        return resource_classes

    def choose_export_resource_class(self, form):
        resource_index = self.get_resource_index(form)
        return self.get_export_resource_classes()[resource_index]

    def get_export_resource_kwargs(self, request, **kwargs):
        return self.get_resource_kwargs(request, **kwargs)

    def get_export_resource_fields_from_from(self, form) -> list[str] | None:
        if isinstance(form, SelectableFieldsExportForm):
            export_fields = form.get_selected_resource_export_fields()
            if export_fields:
                return export_fields

        return

    def get_data_for_export(self, request, queryset, **kwargs):
        export_form = kwargs.get("export_form")
        export_class = self.choose_export_resource_class(export_form)
        export_resource_kwargs = self.get_export_resource_kwargs(request, **kwargs)
        export_fields = self.get_export_resource_fields_from_from(export_form)
        cls = export_class(**export_resource_kwargs)
        export_data = cls.export(
            queryset=queryset, export_fields=export_fields, **kwargs
        )
        return export_data

    def get_export_filename(self, file_format):
        date_str = now().strftime("%Y-%m-%d")
        filename = "%s-%s.%s" % (
            self.model.__name__,
            date_str,
            file_format.get_extension(),
        )
        return filename


class ExportViewMixin(BaseExportMixin):
    form_class = SelectableFieldsExportForm

    def get_export_data(self, file_format, queryset, *args, **kwargs):
        """
        Returns file_format representation for given queryset.
        """
        data = self.get_data_for_export(self.request, queryset, *args, **kwargs)
        export_data = file_format.export_data(data)
        return export_data

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["formats"] = self.get_export_formats()
        kwargs["resources"] = self.get_export_resource_classes()
        return kwargs


class ExportViewFormMixin(ExportViewMixin, FormView):
    def form_valid(self, form):
        warn(
            "ExportViewFormMixin is deprecated and will be removed "
            "in a future release",
            DeprecationWarning,
            stacklevel=2,
        )
        formats = self.get_export_formats()
        file_format = formats[int(form.cleaned_data["format"])]()
        if hasattr(self, "get_filterset"):
            queryset = self.get_filterset(self.get_filterset_class()).qs
        else:
            queryset = self.get_queryset()
        export_data = self.get_export_data(file_format, queryset)
        content_type = file_format.get_content_type()
        # Django 1.7 uses the content_type kwarg instead of mimetype
        try:
            response = HttpResponse(export_data, content_type=content_type)
        except TypeError:
            response = HttpResponse(export_data, mimetype=content_type)
        response["Content-Disposition"] = 'attachment; filename="%s"' % (
            self.get_export_filename(file_format),
        )

        post_export.send(sender=None, model=self.model)
        return response
