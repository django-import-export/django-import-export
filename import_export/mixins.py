from django.http import HttpResponse
from django.utils.timezone import now
from django.views.generic.edit import FormView

from .formats import base_formats
from .forms import ExportForm
from .resources import modelresource_factory
from .signals import post_export


class BaseImportExportMixin:
    formats = base_formats.DEFAULT_FORMATS
    resource_class = None

    def get_resource_class(self):
        if not self.resource_class:
            return modelresource_factory(self.model)
        return self.resource_class

    def get_resource_kwargs(self, request, *args, **kwargs):
        return {}


class BaseImportMixin(BaseImportExportMixin):
    def get_import_resource_class(self):
        """
        Returns ResourceClass to use for import.
        """
        return super().get_resource_class()

    def get_import_formats(self):
        """
        Returns available import formats.
        """
        return [f for f in self.formats if f().can_import()]

    def get_import_resource_kwargs(self, request, *args, **kwargs):
        return super().get_resource_kwargs(request, *args, **kwargs)


class BaseExportMixin(BaseImportExportMixin):
    model = None

    def get_export_formats(self):
        """
        Returns available export formats.
        """
        return [f for f in self.formats if f().can_export()]

    def get_export_resource_class(self):
        """
        Returns ResourceClass to use for export.
        """
        return super().get_resource_class()

    def get_export_resource_kwargs(self, request, *args, **kwargs):
        return super().get_resource_kwargs(request, *args, **kwargs)

    def get_data_for_export(self, request, queryset, *args, **kwargs):
        resource_class = self.get_export_resource_class()
        return resource_class(**self.get_export_resource_kwargs(request, *args, **kwargs))\
            .export(queryset, *args, **kwargs)

    def get_filename(self, file_format):
        date_str = now().strftime('%Y-%m-%d')
        filename = "%s-%s.%s" % (self.model.__name__,
                                 date_str,
                                 file_format.get_extension())
        return filename


class ExportViewMixin(BaseExportMixin):
    form_class = ExportForm

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
        kwargs['formats'] = self.get_export_formats()
        return kwargs


class ExportViewFormMixin(ExportViewMixin, FormView):
    def form_valid(self, form):
        formats = self.get_export_formats()
        file_format = formats[
            int(form.cleaned_data['file_format'])
        ]()
        if hasattr(self, 'get_filterset'):
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
        response['Content-Disposition'] = 'attachment; filename="%s"' % (
            self.get_export_filename(file_format),
        )

        post_export.send(sender=None, model=self.model)
        return response

    def get_export_filename(self, file_format):
        return super().get_filename(file_format)
