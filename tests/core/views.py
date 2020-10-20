from django.views.generic.list import ListView

from import_export import mixins

from . import models


class FiltersetMock:
    filter_field = "test"

    def __init__(self, qs):
        self.qs = qs


class CategoryExportView(mixins.ExportViewFormMixin, ListView):
    model = models.Category


class CategoryExportCustomMethodsView(mixins.ExportViewFormMixin, ListView):
    model = models.Category

    def get_filterset_class(self):
        return FiltersetMock

    def get_filterset(self, filterset_class):
        return filterset_class(self.get_queryset())

    def get_export_filename(self, file_format, *args, **kwargs):
        filterset = kwargs["filterset"]
        filename = "%s.%s" % (filterset.filter_field, file_format.get_extension())
        return filename

    def get_content_disposition(self, filename, *args, **kwargs):
        return 'filename="%s"' % filename
