from __future__ import with_statement

from datetime import datetime
import importlib
import pickle
from django.contrib import admin
from django.utils import six
from django.utils.translation import ugettext_lazy as _
from django.conf.urls import url
from django.template.response import TemplateResponse
from django.contrib import messages
from django.contrib.admin.models import LogEntry, ADDITION, CHANGE, DELETION
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponseRedirect, HttpResponse
try:
    from django.urls import reverse
except ImportError:  # Django<2.0
    from django.core.urlresolvers import reverse
from django.conf import settings
from django.template.defaultfilters import pluralize
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST

from .forms import (
    ImportForm,
    ConfirmImportForm,
    ExportForm,
    export_action_form_factory,
)
from .resources import (
    modelresource_factory,
)
from .formats import base_formats
from .results import RowResult
from .tmp_storages import TempFolderStorage
from .signals import post_export, post_import
from .tasks import export_data

try:
    from django.utils.encoding import force_text
except ImportError:
    from django.utils.encoding import force_unicode as force_text

SKIP_ADMIN_LOG = getattr(settings, 'IMPORT_EXPORT_SKIP_ADMIN_LOG', False)
TMP_STORAGE_CLASS = getattr(settings, 'IMPORT_EXPORT_TMP_STORAGE_CLASS',
                            TempFolderStorage)
USE_CELERY = getattr(settings, 'IMPORT_EXPORT_USE_CELERY', False)
EXPORT_USING_CELERY_LEVEL = getattr(settings, 'IMPORT_EXPORT_EXPORT_USING_CELERY_LEVEL', 0)

if isinstance(TMP_STORAGE_CLASS, six.string_types):
    try:
        # Nod to tastypie's use of importlib.
        parts = TMP_STORAGE_CLASS.split('.')
        module_path, class_name = '.'.join(parts[:-1]), parts[-1]
        module = importlib.import_module(module_path)
        TMP_STORAGE_CLASS = getattr(module, class_name)
    except ImportError as e:
        msg = "Could not import '%s' for import_export setting 'IMPORT_EXPORT_TMP_STORAGE_CLASS'" % TMP_STORAGE_CLASS
        raise ImportError(msg)

#: These are the default formats for import and export. Whether they can be
#: used or not is depending on their implementation in the tablib library.
DEFAULT_FORMATS = (
    base_formats.CSV,
    base_formats.XLS,
    base_formats.XLSX,
    base_formats.TSV,
    base_formats.ODS,
    base_formats.JSON,
    base_formats.YAML,
    base_formats.HTML,
)


def celery_is_present():
    try:
        import celery
        result = True
    except ImportError:
        result = False

    return result


class ImportExportMixinBase(object):
    def get_model_info(self):
        # module_name is renamed to model_name in Django 1.8
        app_label = self.model._meta.app_label
        try:
            return (app_label, self.model._meta.model_name,)
        except AttributeError:
            return (app_label, self.model._meta.module_name,)


class ImportMixin(ImportExportMixinBase):
    """
    Import mixin.
    """

    #: template for change_list view
    change_list_template = 'admin/import_export/change_list_import.html'
    #: template for import view
    import_template_name = 'admin/import_export/import.html'
    #: resource class
    resource_class = None
    #: available import formats
    formats = DEFAULT_FORMATS
    #: import data encoding
    from_encoding = "utf-8"
    skip_admin_log = None
    # storage class for saving temporary files
    tmp_storage_class = None

    def get_skip_admin_log(self):
        if self.skip_admin_log is None:
            return SKIP_ADMIN_LOG
        else:
            return self.skip_admin_log

    def get_tmp_storage_class(self):
        if self.tmp_storage_class is None:
            return TMP_STORAGE_CLASS
        else:
            return self.tmp_storage_class

    def get_urls(self):
        urls = super(ImportMixin, self).get_urls()
        info = self.get_model_info()
        my_urls = [
            url(r'^process_import/$',
                self.admin_site.admin_view(self.process_import),
                name='%s_%s_process_import' % info),
            url(r'^import/$',
                self.admin_site.admin_view(self.import_action),
                name='%s_%s_import' % info),
        ]
        return my_urls + urls

    def get_resource_kwargs(self, request, *args, **kwargs):
        return {}

    def get_import_resource_kwargs(self, request, *args, **kwargs):
        return self.get_resource_kwargs(request, *args, **kwargs)

    def get_resource_class(self):
        if not self.resource_class:
            return modelresource_factory(self.model)
        else:
            return self.resource_class

    def get_import_resource_class(self):
        """
        Returns ResourceClass to use for import.
        """
        return self.get_resource_class()

    def get_import_formats(self):
        """
        Returns available import formats.
        """
        return [f for f in self.formats if f().can_import()]

    @method_decorator(require_POST)
    def process_import(self, request, *args, **kwargs):
        """
        Perform the actual import action (after the user has confirmed the import)
        """

        confirm_form = ConfirmImportForm(request.POST)
        if confirm_form.is_valid():
            import_formats = self.get_import_formats()
            input_format = import_formats[
                int(confirm_form.cleaned_data['input_format'])
            ]()
            tmp_storage = self.get_tmp_storage_class()(name=confirm_form.cleaned_data['import_file_name'])
            data = tmp_storage.read(input_format.get_read_mode())
            if not input_format.is_binary() and self.from_encoding:
                data = force_text(data, self.from_encoding)
            dataset = input_format.create_dataset(data)

            result = self.process_dataset(dataset, confirm_form, request, *args, **kwargs)

            tmp_storage.remove()

            return self.process_result(result, request)

    def process_dataset(self, dataset, confirm_form, request, *args, **kwargs):
        resource = self.get_import_resource_class()(**self.get_import_resource_kwargs(request, *args, **kwargs))
        return resource.import_data(dataset,
                                    dry_run=False,
                                    raise_errors=True,
                                    file_name=confirm_form.cleaned_data['original_file_name'],
                                    user=request.user,
                                    **kwargs)

    def process_result(self, result, request):
        self.generate_log_entries(result, request)
        self.add_success_message(result, request)
        post_import.send(sender=None, model=self.model)

        url = reverse('admin:%s_%s_changelist' % self.get_model_info(),
                      current_app=self.admin_site.name)
        return HttpResponseRedirect(url)

    def generate_log_entries(self, result, request):
        if not self.get_skip_admin_log():
            # Add imported objects to LogEntry
            logentry_map = {
                RowResult.IMPORT_TYPE_NEW: ADDITION,
                RowResult.IMPORT_TYPE_UPDATE: CHANGE,
                RowResult.IMPORT_TYPE_DELETE: DELETION,
            }
            content_type_id = ContentType.objects.get_for_model(self.model).pk
            for row in result:
                if row.import_type != row.IMPORT_TYPE_ERROR and row.import_type != row.IMPORT_TYPE_SKIP:
                    LogEntry.objects.log_action(
                        user_id=request.user.pk,
                        content_type_id=content_type_id,
                        object_id=row.object_id,
                        object_repr=row.object_repr,
                        action_flag=logentry_map[row.import_type],
                        change_message=_("%s through import_export" % row.import_type),
                    )

    def add_success_message(self, result, request):
        opts = self.model._meta

        success_message = _('Import finished, with {} new and ' \
                            '{} updated {}.').format(result.totals[RowResult.IMPORT_TYPE_NEW],
                                                      result.totals[RowResult.IMPORT_TYPE_UPDATE],
                                                      opts.verbose_name_plural)

        messages.success(request, success_message)

    def get_import_context_data(self, **kwargs):
        return self.get_context_data(**kwargs)

    def get_context_data(self, **kwargs):
        return {}

    def get_import_form(self):
        '''
        Get the form type used to read the import format and file.
        '''
        return ImportForm

    def import_action(self, request, *args, **kwargs):
        '''
        Perform a dry_run of the import to make sure the import will not
        result in errors.  If there where no error, save the user
        uploaded file to a local temp file that will be used by
        'process_import' for the actual import.
        '''
        resource = self.get_import_resource_class()(**self.get_import_resource_kwargs(request, *args, **kwargs))

        context = self.get_import_context_data()

        import_formats = self.get_import_formats()
        form_type = self.get_import_form()
        form = form_type(import_formats,
                         request.POST or None,
                         request.FILES or None)

        if request.POST and form.is_valid():
            input_format = import_formats[
                int(form.cleaned_data['input_format'])
            ]()
            import_file = form.cleaned_data['import_file']
            # first always write the uploaded file to disk as it may be a
            # memory file or else based on settings upload handlers
            tmp_storage = self.get_tmp_storage_class()()
            data = bytes()
            for chunk in import_file.chunks():
                data += chunk

            tmp_storage.save(data, input_format.get_read_mode())

            # then read the file, using the proper format-specific mode
            # warning, big files may exceed memory
            try:
                data = tmp_storage.read(input_format.get_read_mode())
                if not input_format.is_binary() and self.from_encoding:
                    data = force_text(data, self.from_encoding)
                dataset = input_format.create_dataset(data)
            except UnicodeDecodeError as e:
                return HttpResponse(_(u"<h1>Imported file has a wrong encoding: %s</h1>" % e))
            except Exception as e:
                return HttpResponse(_(u"<h1>%s encountered while trying to read file: %s</h1>" % (type(e).__name__, import_file.name)))
            result = resource.import_data(dataset, dry_run=True,
                                          raise_errors=False,
                                          file_name=import_file.name,
                                          user=request.user)

            context['result'] = result

            if not result.has_errors():
                context['confirm_form'] = ConfirmImportForm(initial={
                    'import_file_name': tmp_storage.name,
                    'original_file_name': import_file.name,
                    'input_format': form.cleaned_data['input_format'],
                })

        context.update(self.admin_site.each_context(request))

        context['title'] = _("Import")
        context['form'] = form
        context['opts'] = self.model._meta
        context['fields'] = [f.column_name for f in resource.get_user_visible_fields()]

        request.current_app = self.admin_site.name
        return TemplateResponse(request, [self.import_template_name],
                                context)


class ExportMixin(ImportExportMixinBase):
    """
    Export mixin.
    """
    #: resource class
    resource_class = None
    #: template for change_list view
    change_list_template = 'admin/import_export/change_list_export.html'
    #: template for export view
    export_template_name = 'admin/import_export/export.html'
    #: available export formats
    formats = DEFAULT_FORMATS
    #: export data encoding
    to_encoding = "utf-8"

    def get_urls(self):
        urls = super(ExportMixin, self).get_urls()
        my_urls = [
            url(r'^export/$',
                self.admin_site.admin_view(self.export_action),
                name='%s_%s_export' % self.get_model_info()),
        ]
        return my_urls + urls

    def get_resource_kwargs(self, request, *args, **kwargs):
        return {}

    def get_export_resource_kwargs(self, request, *args, **kwargs):
        return self.get_resource_kwargs(request, *args, **kwargs)

    def get_resource_class(self):
        if not self.resource_class:
            return modelresource_factory(self.model)
        else:
            return self.resource_class

    def get_export_resource_class(self):
        """
        Returns ResourceClass to use for export.
        """
        return self.get_resource_class()

    def get_export_formats(self):
        """
        Returns available export formats.
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
                        list_display_links, self.list_filter,
                        self.date_hierarchy, self.search_fields,
                        self.list_select_related, self.list_per_page,
                        self.list_max_show_all, self.list_editable,
                        self)

        return cl.queryset

    def get_export_data(self, file_format, queryset, *args, **kwargs):
        """
        Returns file_format representation for given queryset.
        """
        request = kwargs.pop("request")
        resource_class = self.get_export_resource_class()
        data = resource_class(**self.get_export_resource_kwargs(request)).export(queryset, *args, **kwargs)
        export_data = file_format.export_data(data)
        return export_data

    def get_export_context_data(self, **kwargs):
        return self.get_context_data(**kwargs)

    def get_context_data(self, **kwargs):
        return {}

    def handle_export(self, file_format, queryset, *args, **kwargs):
        request = kwargs.get("request")

        if celery_is_present() and USE_CELERY and queryset.count() > EXPORT_USING_CELERY_LEVEL:
            file_format_name = str(file_format.__name__)
            model_name = self.get_model_info()[1]
            model_name = model_name.capitalize()
            subject_line = model_name + str(_(' Data Export'))

            resource_class = self.get_export_resource_class()
            resource_kwargs = self.get_export_resource_kwargs(request)
            resource_class_import_path = '%s.%s' % (resource_class.__module__, resource_class.__name__)

            result = export_data.delay(file_format_name, pickle.dumps(queryset.query), resource_class_import_path, resource_kwargs, request.user.id, subject_line)
        else:
            file_format_instance = file_format()
            exported_data = self.get_export_data(file_format_instance, queryset, request=request)
            content_type = file_format_instance.get_content_type()
            result = HttpResponse(exported_data, content_type=content_type)
            result['Content-Disposition'] = 'attachment; filename=%s' % (
                self.get_export_filename(file_format_instance),
            )

        if isinstance(result, HttpResponse):
            response = result
        else:
            response = self.process_export_result(request)

        return response

    def process_export_result(self, request):
        self.add_successful_export_message(request)
        post_export.send(sender=None, model=self.model)

        url = reverse('admin:%s_%s_changelist' % self.get_model_info(),
                      current_app=self.admin_site.name)
        return HttpResponseRedirect(url)

    def add_successful_export_message(self, request):
        success_message = _("Data export in progress. When it's done, you will get an email with a url where you can download the results.")
        messages.success(request, success_message)

    def export_action(self, request, *args, **kwargs):
        formats = self.get_export_formats()
        form = ExportForm(formats, request.POST or None)
        if form.is_valid():
            file_format = formats[
                int(form.cleaned_data['file_format'])
            ]

            queryset = self.get_export_queryset(request)
            response = self.handle_export(file_format, queryset, request=request)

            post_export.send(sender=None, model=self.model)
            return response

        context = self.get_export_context_data()

        context.update(self.admin_site.each_context(request))

        context['title'] = _("Export")
        context['form'] = form
        context['opts'] = self.model._meta
        request.current_app = self.admin_site.name
        return TemplateResponse(request, [self.export_template_name],
                                context)


class ImportExportMixin(ImportMixin, ExportMixin):
    """
    Import and export mixin.
    """
    #: template for change_list view
    change_list_template = 'admin/import_export/change_list_import_export.html'


class ImportExportModelAdmin(ImportExportMixin, admin.ModelAdmin):
    """
    Subclass of ModelAdmin with import/export functionality.
    """


class ExportActionModelAdmin(ExportMixin, admin.ModelAdmin):
    """
    Subclass of ModelAdmin with export functionality implemented as an
    admin action.
    """

    # Don't use custom change list template.
    change_list_template = None

    def __init__(self, *args, **kwargs):
        """
        Adds a custom action form initialized with the available export
        formats.
        """
        choices = []
        formats = self.get_export_formats()
        if formats:
            choices.append(('', '---'))
            for i, f in enumerate(formats):
                choices.append((str(i), f().get_title()))

        self.action_form = export_action_form_factory(choices)
        super(ExportActionModelAdmin, self).__init__(*args, **kwargs)

    def export_admin_action(self, request, queryset):
        """
        Exports the selected rows using file_format.
        """
        export_format = request.POST.get('file_format')

        if not export_format:
            messages.warning(request, _('You must select an export format.'))
        else:
            formats = self.get_export_formats()
            file_format = formats[int(export_format)]

            response = self.handle_export(file_format, queryset, request=request)
            return response
    export_admin_action.short_description = _(
        'Export selected %(verbose_name_plural)s')

    actions = [export_admin_action]

    class Media:
        js = ['import_export/action_formats.js']


class ImportExportActionModelAdmin(ImportMixin, ExportActionModelAdmin):
    """
    Subclass of ExportActionModelAdmin with import/export functionality.
    Export functionality is implemented as an admin action.
    """
