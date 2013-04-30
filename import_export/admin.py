from __future__ import with_statement

import os
import tempfile
from datetime import datetime

from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from django.conf.urls import patterns, url
from django.template.response import TemplateResponse
from django.contrib import messages
from django.http import HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse

from .forms import (
        ImportForm,
        ConfirmImportForm,
        ExportForm,
        )
from .resources import (
        modelresource_factory,
        )
from .formats import base_formats


DEFAULT_FORMATS = (
            base_formats.CSV,
            base_formats.XLS,
            base_formats.TSV,
            base_formats.ODS,
            base_formats.JSON,
            base_formats.YAML,
            base_formats.HTML,
            )


class ImportMixin(object):
    """
    Import mixin.
    """

    change_list_template = 'admin/import_export/change_list_import.html'
    import_template_name = 'admin/import_export/import.html'
    resource_class = None
    formats = DEFAULT_FORMATS
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

    def get_import_formats(self):
        """
        Returns available import formats.
        """
        return [f for f in self.formats if f().can_import()]

    def process_import(self, request, *args, **kwargs):
        '''
        Perform the actuall import action (after the user has confirmed he wishes to import)
        '''
        opts = self.model._meta
        resource = self.get_resource_class()()

        confirm_form = ConfirmImportForm(request.POST)
        if confirm_form.is_valid():
            import_formats = self.get_import_formats()
            input_format = import_formats[
                    int(confirm_form.cleaned_data['input_format'])
                    ]()
            import_file = open(confirm_form.cleaned_data['import_file_name'],
                    input_format.get_read_mode())
            data = import_file.read()
            if not input_format.is_binary() and self.from_encoding:
                data = unicode(data, self.from_encoding).encode('utf-8')
            dataset = input_format.create_dataset(data)

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
        '''
        Perform a dry_run of the import to make sure the import will not result in errors.
        If there where no error, save the the user uploaded file to a local temp file that 
        will be used by 'process_import' for the actual import.
        '''
        resource = self.get_resource_class()()

        context = {}

        import_formats = self.get_import_formats()
        form = ImportForm(import_formats,
                request.POST or None,
                request.FILES or None)

        if request.POST and form.is_valid():
            input_format = import_formats[
                    int(form.cleaned_data['input_format'])
                    ]()
            import_file = form.cleaned_data['import_file']
            # first always write the uploaded file to disk as it may be a 
            # memory file or else based on settings upload handlers
            with tempfile.NamedTemporaryFile(delete=False) as uploaded_file:
                 for chunk in import_file.chunks():
                     uploaded_file.write(chunk)

            # then read the file, using the proper format-specific mode
            with open(uploaded_file.name, input_format.get_read_mode()) as uploaded_import_file:
                # warning, big files may exceed memory
                data = uploaded_import_file.read()
                if not input_format.is_binary() and self.from_encoding:
                    data = unicode(data, self.from_encoding).encode('utf-8')
                dataset = input_format.create_dataset(data)
                result = resource.import_data(dataset, dry_run=True,
                        raise_errors=False)

            context['result'] = result

            if not result.has_errors():
                context['confirm_form'] = ConfirmImportForm(initial={
                    'import_file_name': uploaded_file.name,
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
    export_template_name = 'admin/import_export/export.html'
    formats = DEFAULT_FORMATS
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

    def get_export_formats(self):
        """
        Returns available import formats.
        """
        return [f for f in self.formats if f().can_export()]

    def get_export_filename(self, file_format):
        date_str = datetime.now().strftime('%Y-%m-%d')
        filename = "%s-%s.%s" % (self.model.__name__,
                date_str,
                file_format.get_extension())
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
        formats = self.get_export_formats()
        form = ExportForm(formats, request.POST or None)
        if form.is_valid():
            file_format = formats[
                    int(form.cleaned_data['file_format'])
                    ]()

            resource_class = self.get_resource_class()
            queryset = self.get_export_queryset(request)
            data = resource_class().export(queryset)
            response = HttpResponse(
                    file_format.export_data(data),
                    mimetype='application/octet-stream',
                    )
            response['Content-Disposition'] = 'attachment; filename=%s' % (
                   self.get_export_filename(file_format),
                   )
            return response

        context = {}
        context['form'] = form
        context['opts'] = self.model._meta
        return TemplateResponse(request, [self.export_template_name],
                context, current_app=self.admin_site.name)


class ImportExportMixin(ImportMixin, ExportMixin):
    """
    Import and export mixin.
    """
    change_list_template = 'admin/import_export/change_list_import_export.html'


class ImportExportModelAdmin(ImportExportMixin, admin.ModelAdmin):
    """
    Subclass of ModelAdmin with import/export functionality.
    """
