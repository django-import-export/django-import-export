from __future__ import with_statement

import tempfile
from datetime import datetime
import os.path

from django.contrib import admin
from django.db.models import fields
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _
from django.conf.urls import patterns, url
from django.template.response import TemplateResponse
from django.contrib import messages
from django.contrib.admin.models import LogEntry, ADDITION, CHANGE, DELETION
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse

from .forms import (
    ImportForm,
    ConfirmImportForm,
    ExportForm,
    export_action_form_factory,
)
from .resources import (
    modelresource_factory,
    ModelResource,
    ModelDeclarativeMetaclass
)
from .formats import base_formats
from .results import RowResult

try:
    from django.utils.encoding import force_text
except ImportError:
    from django.utils.encoding import force_unicode as force_text


#: import / export formats
DEFAULT_FORMATS = (
    base_formats.CSV,
    base_formats.XLS,
    base_formats.TSV,
    base_formats.ODS,
    base_formats.JSON,
    base_formats.YAML,
    base_formats.HTML,
)


class ImportExportMixinBase(object):
    """
    Goodies used by all classes to come, whether they be Import, Export,
    RelatedImport, RelatedImportable, or any combination
    """
    #: resource class
    resource_class = None
    #: available import formats
    formats = DEFAULT_FORMATS
    #: import data encoding
    from_encoding = "utf-8"

    def get_model_info(self):
        # module_name is renamed to model_name in Django 1.8
        app_label = self.model._meta.app_label
        try:
            return (app_label, self.model._meta.model_name,)
        except AttributeError:
            return (app_label, self.model._meta.module_name,)

    def get_resource_class_attrs(self):
        return {}

    def get_resource_meta_attrs(self):
        return {}

    def get_resource_class(self):
        if not self.resource_class:
            return modelresource_factory(self.model, self.get_resource_meta_attrs(), self.get_resource_class_attrs())
        else:
            return self.resource_class


class ImportMixin(ImportExportMixinBase):
    """
    Import mixin.
    """

    #: template for change_list view
    change_list_template = 'admin/import_export/change_list_import.html'
    #: template for import view
    import_template_name = 'admin/import_export/import.html'

    def get_urls(self):
        urls = super(ImportMixin, self).get_urls()
        info = self.get_model_info()
        my_urls = patterns(
            '',
            url(r'^process_import/$',
                self.admin_site.admin_view(self.process_import),
                name='%s_%s_process_import' % info),
            url(r'^import/$',
                self.admin_site.admin_view(self.import_action),
                name='%s_%s_import' % info),
        )
        return my_urls + urls

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

    def get_confirm_form_class(self):
        return ConfirmImportForm

    def get_confirm_form_initial(self, import_form, uploaded_file):
        return {
            'import_file_name': os.path.basename(uploaded_file.name),
            'input_format': import_form.cleaned_data['input_format'],
        }

    def get_import_form_class(self):
        return ImportForm

    def get_import_form_initial_args(self):
        return (self.get_import_formats(),
            self.request.POST or None, self.request.FILES or None,)

    def get_import_form_initial_kwargs(self):
        return {}

    def get_process_redirect_url(self):
        return reverse('admin:%s_%s_changelist' % self.get_model_info(),
                       current_app=self.admin_site.name)

    def process_import(self, request, *args, **kwargs):
        '''
        Perform the actual import action (after the user has confirmed he
        wishes to import)
        '''
        opts = self.get_opts()
        resource = self.get_import_resource_class()()

        confirm_form = self.get_confirm_form_class()(request.POST)
        if confirm_form.is_valid():
            import_formats = self.get_import_formats()
            input_format = import_formats[
                int(confirm_form.cleaned_data['input_format'])
            ]()
            import_file_name = os.path.join(
                tempfile.gettempdir(),
                confirm_form.cleaned_data['import_file_name']
            )
            import_file = open(import_file_name, input_format.get_read_mode())
            data = import_file.read()
            if not input_format.is_binary() and self.from_encoding:
                data = force_text(data, self.from_encoding)
            data = self.finalize_data(data)

            dataset = input_format.create_dataset(data)
            dataset = self.finalize_dataset(dataset)

            result = resource.import_data(dataset, dry_run=False,
                                 raise_errors=True)

            # Add imported objects to LogEntry
            logentry_map = {
                RowResult.IMPORT_TYPE_NEW: ADDITION,
                RowResult.IMPORT_TYPE_UPDATE: CHANGE,
                RowResult.IMPORT_TYPE_DELETE: DELETION,
            }
            content_type_id = ContentType.objects.get_for_model(self.model).pk
            for row in result:
                if row.import_type != row.IMPORT_TYPE_SKIP:
                    LogEntry.objects.log_action(
                        user_id=request.user.pk,
                        content_type_id=content_type_id,
                        object_id=row.object_id,
                        object_repr=row.object_repr,
                        action_flag=logentry_map[row.import_type],
                        change_message="%s through import_export" % row.import_type,
                    )

            success_message = _('Import finished')
            messages.success(request, success_message)
            import_file.close()

            url = self.get_process_redirect_url()
            return HttpResponseRedirect(url)
        else:
            self.get_logger().error(confirm_form.errors)

    def finalize_data(self, data):
        return data

    def finalize_dataset(self, dataset):
        return dataset

    def get_field_names(self, resource):
        return [f.column_name for f in resource.get_fields()]

    def get_confirmation_action_urlname_trailing_component(self):
        return 'process_import'

    @property
    def model_name(self):
        try:
            # 1.6+
            return self.get_opts().model_name
        except AttributeError:
            # <= 1.5
            return self.get_opts().object_name.lower()

    def get_confirmation_action_urlname(self, arg=None):
        arg = arg or self.get_confirmation_action_urlname_trailing_component()

        return 'admin:%s_%s_%s' % (self.get_opts().app_label, self.model_name, arg)

    def get_confirmation_action_url(self):
        return reverse(self.get_confirmation_action_urlname())

    def get_opts(self):
        return self.model._meta

    def _import_action(self, request, *args, **kwargs):
        '''
        Perform a dry_run of the import to make sure the import will not
        result in errors.  If there where no error, save the user
        uploaded file to a local temp file that will be used by
        'process_import' for the actual import.
        '''
        resource = self.get_import_resource_class()()

        context = {}

        form = self.get_import_form_class()(
            *self.get_import_form_initial_args(),
            **self.get_import_form_initial_kwargs())

        if request.POST and form.is_valid():
            input_format = self.get_import_formats()[
                int(form.cleaned_data['input_format'])
            ]()
            import_file = form.cleaned_data['import_file']
            # first always write the uploaded file to disk as it may be a
            # memory file or else based on settings upload handlers
            with tempfile.NamedTemporaryFile(delete=False) as uploaded_file:
                for chunk in import_file.chunks():
                    uploaded_file.write(chunk)

            # then read the file, using the proper format-specific mode
            with open(uploaded_file.name,
                      input_format.get_read_mode()) as uploaded_import_file:
                # warning, big files may exceed memory
                data = uploaded_import_file.read()
                data = self.finalize_data(data)
                if not input_format.is_binary() and self.from_encoding:
                    data = force_text(data, self.from_encoding)
                dataset = input_format.create_dataset(data)
                dataset = self.finalize_dataset(dataset)
                result = resource.import_data(dataset, dry_run=True,
                                              raise_errors=False)

            context['result'] = result

            if not result.has_errors():
                context['confirm_form'] = self.get_confirm_form_class()(
                    initial=self.get_confirm_form_initial(form, uploaded_file)
                )
                context['confirmation_action_url'] = self.get_confirmation_action_url()

        context['form'] = form
        context['opts'] = self.get_opts()
        context['fields'] = self.get_field_names(resource)
        return context

    def import_action(self, request, *args, **kwargs):
        # In line with some CBV standards
        self.request = request
        self.args = args
        self.kwargs = kwargs

        context = self._import_action(request, *args, **kwargs)
        return TemplateResponse(request, [self.import_template_name],
                                context, current_app=self.admin_site.name)


class RelatedModelImporterMixin(ImportMixin):
    """
    Teaches an AdminModel how to read and use a class-level attr `related_importables`,
    populated with RelatedModelImportableAdmin-extending classes.

    Inherits from ImportMixin because this class cannot stand on its own.
    """
    related_importables = []
    change_form_template = 'admin/import_export/change_form_import_related.html'

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['related_importable_links'] = self.get_related_import_links(object_id)
        return super(RelatedModelImporterMixin, self).change_view(request, object_id, form_url, extra_context)

    def get_related_import_links(self, object_id):
        links = []
        for related_importable in self.related_importables:
            # Make an instance of the dealio
            related_importable = related_importable(admin_site=self.admin_site)

            info = self.get_related_importable_admin_urlname_info(related_importable)
            links.append({
                'display_name': related_importable.model._meta.verbose_name_plural,
                'url': reverse('admin:%s_%s_import_%s_action' % (info), args=(object_id,))
            })
        return links

    def get_related_importable_admin_urlname_info(self, related_importable):
        # Prepare a generic name for the admin URL
        return self.model._meta.app_label, self.model_name, related_importable.get_sluggy_verbose_name()

    def get_urls(self):
        """
        Extends ``get_urls()`` to add Views for each ``related_importable``
        """
        urls = super(RelatedModelImporterMixin, self).get_urls()
        my_urls = patterns('',)

        for related_importable in self.related_importables:
            # Make an instance of the dealio
            related_importable = related_importable(admin_site=self.admin_site)
            assert isinstance(related_importable, RelatedModelImportableAdmin), "All ``related_importables`` must subclass ``RelatedModelImporterMixin``"

            info = self.get_related_importable_admin_urlname_info(related_importable)

            my_urls += patterns('',
                url(r'^(.+)/import_%s/$' % (related_importable.get_sluggy_verbose_name(),),
                    self.admin_site.admin_view(related_importable.import_action),
                    name='%s_%s_import_%s_action' % info),
                url(r'^(.+)/process_%s_import/$' % (related_importable.get_sluggy_verbose_name(),),
                    self.admin_site.admin_view(related_importable.process_import),
                    name='%s_%s_process_%s_import' % info),
            )

        return my_urls + urls


class ExportMixin(ImportExportMixinBase):
    """
    Export mixin.
    """
    #: template for change_list view
    change_list_template = 'admin/import_export/change_list_export.html'
    #: template for export view
    export_template_name = 'admin/import_export/export.html'

    def get_urls(self):
        urls = super(ExportMixin, self).get_urls()
        my_urls = patterns(
            '',
            url(r'^export/$',
                self.admin_site.admin_view(self.export_action),
                name='%s_%s_export' % self.get_model_info()),
        )
        return my_urls + urls

    def get_export_resource_class(self):
        """
        Returns ResourceClass to use for export.
        """
        return self.get_resource_class()

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
                        list_display_links, self.list_filter,
                        self.date_hierarchy, self.search_fields,
                        self.list_select_related, self.list_per_page,
                        self.list_max_show_all, self.list_editable,
                        self)

        # query_set has been renamed to queryset in Django 1.8
        try:
            return cl.queryset
        except AttributeError:
            return cl.query_set

    def get_export_data(self, file_format, queryset):
        """
        Returns file_format representation for given queryset.
        """
        resource_class = self.get_export_resource_class()
        data = resource_class().export(queryset)
        export_data = file_format.export_data(data)
        return export_data

    def export_action(self, request, *args, **kwargs):
        formats = self.get_export_formats()
        form = ExportForm(formats, request.POST or None)
        if form.is_valid():
            file_format = formats[
                int(form.cleaned_data['file_format'])
            ]()

            queryset = self.get_export_queryset(request)
            export_data = self.get_export_data(file_format, queryset)
            content_type = 'application/octet-stream'
            # Django 1.7 uses the content_type kwarg instead of mimetype
            try:
                response = HttpResponse(export_data, content_type=content_type)
            except TypeError:
                response = HttpResponse(export_data, mimetype=content_type)
            response['Content-Disposition'] = 'attachment; filename=%s' % (
                self.get_export_filename(file_format),
            )
            return response

        context = {}
        context['form'] = form
        context['opts'] = self.model._meta

        return TemplateResponse(request, [self.export_template_name],
                                context, current_app=self.admin_site.name)


class RelatedModelImportableAdmin(ImportMixin):
    """
    The parent class for related importables. Inheriting classes will get
    declared on their host ModelAdmin in a fashion similar to Inlines.
    """
    resource_exclude = ()

    def __init__(self, *args, **kwargs):
        self.admin_site = kwargs.pop('admin_site')
        super(RelatedModelImportableAdmin, self).__init__(*args, **kwargs)

    def _import_action(self, request, *args, **kwargs):
        context = super(RelatedModelImportableAdmin, self)._import_action(
            request, *args, **kwargs)

        context['instance'] = get_object_or_404(self.origin_model, pk=self.args[0])
        return context

    def get_sluggy_verbose_name(self):
        return self.model._meta.verbose_name_plural.lower().replace(' ', '_')

    def get_implied_origin_model(self):
        return self.origin_model._default_manager.get(pk=self.args[0])

    @property
    def origin_model_name(self):
        try:
            # >= 1.6
            return self.origin_model._meta.model_name
        except AttributeError:
            # <= 1.5
            return self.origin_model._meta.object_name.lower()

    def finalize_dataset(self, dataset):
        # Make a list of appropriate length, containing only our implied origin model's PK
        origin_model_instance = self.get_implied_origin_model()
        importer_id_list = [origin_model_instance.pk] * len(dataset)

        # Update the dataset to include that column
        dataset.append_col(importer_id_list, header=self.get_relation_field_name())

        return dataset

    def get_process_redirect_url(self):
        url_name = 'admin:%s_%s_change' % (self.origin_model._meta.app_label, self.origin_model_name,)
        return reverse(url_name, args=self.args)

    def get_default_include_excludes(self):
        """
        Place to programmatically select which attribute is set in the
        default resource. Defaults to `exclude` and an empty tuple.
        """
        return 'exclude', self.get_excludes()

    def get_resource_meta_attrs(self):
        # Begin by calling the super() version
        meta_attrs = super(RelatedModelImportableAdmin, self).get_resource_meta_attrs()

        # Because ``include`` and ``exclude`` are mutually exclusive,
        # only one of the two keys should appear
        include_exclude_key, include_exclude_values = self.get_default_include_excludes()

        meta_attrs['include_exclude_key'] = include_exclude_values
        return meta_attrs

    def get_resource_class(self):
        """
        Override hook if you've already customized a Resource for the related model.
        """
        if hasattr(self, 'resource_class') and bool(self.resource_class):
            return self.resource_class

        # Compile meta_attrs
        meta_attrs = self.get_resource_meta_attrs()
        meta_attrs['model'] = self.model

        Meta = type(str('Meta'), (object,), meta_attrs)

        class_name = str('Related') + self.model.__name__ + str('Resource')
        class_attrs = self.get_resource_class_attrs()
        class_attrs['Meta'] = Meta

        metaclass = ModelDeclarativeMetaclass
        return metaclass(class_name, (ModelResource,), class_attrs)

    def get_excludes(self):
        return self.resource_exclude

    def get_opts(self):
        return self.origin_model._meta

    def get_confirmation_action_urlname_trailing_component(self):
        return 'process_%s_import' % (self.model._meta.verbose_name_plural.lower().replace(' ', '_'))

    def get_confirmation_action_url(self):
        """
        Override the normal URL builder to supply the necessary positional
        argument for successful reversal.
        """
        return reverse(self.get_confirmation_action_urlname(), args=(self.args[0],))

    def get_relation_field_name(self):
        for field in self.model._meta.fields:
            # The relationship obviously must be a related field
            if isinstance(field, fields.related.RelatedField):
                # ``issubclass`` returns True for parental relationships and when
                # simply passing the same class twice
                if issubclass(self.origin_model, field.related.parent_model):
                    return field.name
        raise Exception("Could not find pointer from %s to %s" % (self.model.__name__, self.origin_model.__name__,))


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
            file_format = formats[int(export_format)]()

            export_data = self.get_export_data(file_format, queryset)
            content_type = 'application/octet-stream'
            # Django 1.7 uses the content_type kwarg instead of mimetype
            try:
                response = HttpResponse(export_data, content_type=content_type)
            except TypeError:
                response = HttpResponse(export_data, mimetype=content_type)
            response['Content-Disposition'] = 'attachment; filename=%s' % (
                self.get_export_filename(file_format),
            )
            return response
    export_admin_action.short_description = _(
        'Export selected %(verbose_name_plural)s')

    actions = [export_admin_action]


class ImportExportActionModelAdmin(ImportMixin, ExportActionModelAdmin):
    """
    Subclass of ExportActionModelAdmin with import/export functionality.
    Export functionality is implemented as an admin action.
    """


class ImportRelatedModelImporterMixin(RelatedModelImporterMixin, admin.ModelAdmin):
    """
    Subclass of ModelAdmin with import/related-model-import functionality.
    """


class ImportExportRelatedModelImporterMixin(RelatedModelImporterMixin, ExportMixin, admin.ModelAdmin):
    """
    Subclass of ModelAdmin with import/export/related-model-import functionality.
    """
