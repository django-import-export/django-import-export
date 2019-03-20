from django.views.generic.list import ListView

from import_export import mixins

from . import models


class CategoryExportView(mixins.ExportViewFormMixin, ListView):
    model = models.Category
