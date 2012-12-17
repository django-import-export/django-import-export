import tempfile
from datetime import datetime

import tablib

from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from django.conf.urls.defaults import patterns, url
from django.template.response import TemplateResponse
from django.contrib import messages
from django.http import HttpResponseRedirect, HttpResponse
from django.utils.importlib import import_module
from django.core.urlresolvers import reverse

from .forms import (
        ImportForm,
        ConfirmImportForm,
        )
from .resources import (
        modelresource_factory,
        )


class ImportMixin(object):
    """
    Import mixin.
    """

    change_list_template = 'admin/import_export/change_list_import.html'
    import_template_name = 'admin/import_export/import.html'
    resource_class = None
    format_choices = (
            ('', '---'),
            ('tablib.formats._csv', 'CSV'),
            )
    from_encoding = "utf-8"

    def get_urls(self):
        urls = super(ImportMixin, self).get_urls()
        info = self.model._meta.app_label, self.model._meta.module_name
        my_urls = patterns('',
            url(r'^process_import/$',
                self.admin_site.admin_view(self.process_import),
                name='%s_%s_process_import' % info),
            url(r'^import/$',
                self.admin_site.admin_view(self.import_action),
                name='%s_%s_import' % info),
        )
        return my_urls + urls

    def get_resource_class(self):
        if not self.resource_class:
            return modelresource_factory(self.model)
        else:
            return self.resource_class

    def get_format(self, format_class):
        if format_class:
            return import_module(format_class)
        return None

    def get_mode_for_format(self, format):
        """
        Returns mode for opening files.
        """
        return 'rU'

    def load_dataset(self, stream, input_format=None, from_encoding=None):
        """
        Loads data from ``stream`` given valid tablib ``input_format``
        and returns tablib dataset

        If ``from_encoding`` is specified, data will be converted to `utf-8`
        characterset.
        """
        if from_encoding:
            text = unicode(stream.read(), from_encoding).encode('utf-8')
        else:
            text = stream.read()
        if not input_format:
            data = tablib.import_set(text)
        else:
            data = tablib.Dataset()
            input_format.import_set(data, text)
        return data

    def process_import(self, request, *args, **kwargs):
        opts = self.model._meta
        resource = self.get_resource_class()()

        confirm_form = ConfirmImportForm(request.POST)
        if confirm_form.is_valid():
            input_format = self.get_format(
                    confirm_form.cleaned_data['input_format'])
            import_mode = self.get_mode_for_format(input_format)
            import_file = open(confirm_form.cleaned_data['import_file_name'],
                    import_mode)

            dataset = self.load_dataset(import_file, input_format,
                    self.from_encoding)
            resource.import_data(dataset, dry_run=False,
                    raise_errors=True)

            success_message = _('Import finished')
            messages.success(request, success_message)
            import_file.close()

            url = reverse('admin:%s_%s_changelist' %
                               (opts.app_label, opts.module_name),
                               current_app=self.admin_site.name)
            return HttpResponseRedirect(url)

    def import_action(self, request, *args, **kwargs):
        resource = self.get_resource_class()()

        context = {}

        form = ImportForm(self.format_choices,
                request.POST or None,
                request.FILES or None)

        if request.POST:
            if form.is_valid():
                input_format = self.get_format(
                        form.cleaned_data['input_format'])
                import_mode = self.get_mode_for_format(input_format)
                import_file = form.cleaned_data['import_file']
                import_file.open(import_mode)

                dataset = self.load_dataset(import_file, input_format,
                        self.from_encoding)
                result = resource.import_data(dataset, dry_run=True,
                        raise_errors=False)

                context['result'] = result

                if not result.has_errors():
                    tmp_file = tempfile.NamedTemporaryFile(delete=False)
                    for chunk in import_file.chunks():
                        tmp_file.write(chunk)
                    tmp_file.close()
                    context['confirm_form'] = ConfirmImportForm(initial={
                        'import_file_name': tmp_file.name,
                        'input_format': form.cleaned_data['input_format'],
                        })

        context['form'] = form
        context['opts'] = self.model._meta
        context['fields'] = [f.column_name for f in resource.get_fields()]

        return TemplateResponse(request, [self.import_template_name],
                context, current_app=self.admin_site.name)


class ExportMixin(object):
    """
    Export mixin.
    """
    resource_class = None
    change_list_template = 'admin/import_export/change_list_export.html'
    export_format = 'csv'
    to_encoding = "utf-8"

    def get_urls(self):
        urls = super(ExportMixin, self).get_urls()
        info = self.model._meta.app_label, self.model._meta.module_name
        my_urls = patterns('',
            url(r'^export/$',
                self.admin_site.admin_view(self.export_action),
                name='%s_%s_export' % info),
        )
        return my_urls + urls

    def get_resource_class(self):
        if not self.resource_class:
            return modelresource_factory(self.model)
        else:
            return self.resource_class

    def get_export_filename(self):
        date_str = datetime.now().strftime('%Y-%m-%d')
        filename = "%s-%s.%s" % (self.model.__name__,
                date_str, self.export_format)
        return filename

    def get_export_queryset(self, request):
        """
        Returns export queryset.

        Default implementation respects applied search and filters.
        """
        # copied from django/contrib/admin/options.py
        list_display = self.get_list_display(request)
        list_display_links = self.get_list_display_links(request, list_display)

        ChangeList = self.get_changelist(request)
        cl = ChangeList(request, self.model, list_display,
            list_display_links, self.list_filter, self.date_hierarchy,
            self.search_fields, self.list_select_related,
            self.list_per_page, self.list_max_show_all, self.list_editable,
            self)

        return cl.query_set

    def export_action(self, request, *args, **kwargs):
        resource_class = self.get_resource_class()
        queryset = self.get_export_queryset(request)
        data = resource_class().export(queryset)
        filename = self.get_export_filename()
        response = HttpResponse(
                getattr(data, self.export_format),
                mimetype='application/octet-stream',
                )
        response['Content-Disposition'] = 'attachment; filename=%s' % filename
        return response


class ImportExportMixin(ImportMixin, ExportMixin):
    """
    Import and export mixin.
    """
    change_list_template = 'admin/import_export/change_list_import_export.html'


class ImportExportModelAdmin(ImportExportMixin, admin.ModelAdmin):
    """
    Subclass of ModelAdmin with import/export functionality.
    """
