from django.http import HttpResponse
from django.views.generic.edit import FormView
from django.utils.timezone import now

from .formats import base_formats
from .resources import modelresource_factory
from .signals import post_export
from .forms import ExportForm


class ExportViewMixin(object):
    formats = base_formats.DEFAULT_FORMATS
    form_class = ExportForm
    resource_class = None

    def get_export_formats(self):
        """
        Returns available export formats.
        """
        return [f for f in self.formats if f().can_export()]

    def get_resource_class(self):
        if not self.resource_class:
            return modelresource_factory(self.model)
        return self.resource_class

    def get_export_resource_class(self):
        """
        Returns ResourceClass to use for export.
        """
        return self.get_resource_class()

    def get_resource_kwargs(self, request, *args, **kwargs):
        return {}

    def get_export_resource_kwargs(self, request, *args, **kwargs):
        return self.get_resource_kwargs(request, *args, **kwargs)

    def get_export_data(self, file_format, queryset, *args, **kwargs):
        """
        Returns file_format representation for given queryset.
        """
        resource_class = self.get_export_resource_class()
        data = resource_class(**self.get_export_resource_kwargs(self.request))\
            .export(queryset, *args, **kwargs)
        export_data = file_format.export_data(data)
        return export_data

    def get_export_filename(self, file_format):
        date_str = now().strftime('%Y-%m-%d')
        filename = "%s-%s.%s" % (self.model.__name__,
                                 date_str,
                                 file_format.get_extension())
        return filename

    def get_context_data(self, **kwargs):
        context = super(ExportViewMixin, self).get_context_data(**kwargs)
        return context

    def get_form_kwargs(self):
        kwargs = super(ExportViewMixin, self).get_form_kwargs()
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
        response['Content-Disposition'] = 'attachment; filename=%s' % (
            self.get_export_filename(file_format),
        )

        post_export.send(sender=None, model=self.model)
        return response
