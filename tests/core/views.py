import warnings

from django.views.generic.list import ListView

from import_export import mixins

from . import models

with warnings.catch_warnings():
    warnings.simplefilter("ignore", category=DeprecationWarning)

    class CategoryExportView(mixins.ExportViewFormMixin, ListView):
        model = models.Category
