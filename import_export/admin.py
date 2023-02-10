import logging
import warnings

import django
from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.admin.models import ADDITION, CHANGE, DELETION, LogEntry
from django.contrib.auth import get_permission_codename
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.decorators import method_decorator
from django.utils.module_loading import import_string
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from .formats.base_formats import DEFAULT_FORMATS
from .forms import (
    ConfirmImportForm,
    ExportForm,
    ImportExportFormBase,
    ImportForm,
    export_action_form_factory,
)
from .mixins import BaseExportMixin, BaseImportMixin
from .results import RowResult
from .signals import post_export, post_import
from .tmp_storages import MediaStorage, TempFolderStorage
from .utils import original

logger = logging.getLogger(__name__)


class ImportExportMixinBase:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.init_change_list_template()

    def init_change_list_template(self):
        # Store already set change_list_template to allow users to independently
        # customize the change list object tools. This treats the cases where
        # `self.change_list_template` is `None` (the default in `ModelAdmin`) or
        # where `self.import_export_change_list_template` is `None` as falling
        # back on the default templates.
        if getattr(self, 'change_list_template', None):
            self.base_change_list_template = self.change_list_template
        else:
            self.base_change_list_template = 'admin/change_list.html'

        try:
            self.change_list_template = getattr(
                self, 'import_export_change_list_template', None
            )
        except AttributeError:
            logger.warning("failed to assign change_list_template attribute (see issue 1521)")

        if self.change_list_template is None:
            self.change_list_template = self.base_change_list_template

    def get_model_info(self):
        app_label = self.model._meta.app_label
        return (app_label, self.model._meta.model_name)

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['base_change_list_template'] = self.base_change_list_template
        return super().changelist_view(request, extra_context)


class ImportMixin(BaseImportMixin, ImportExportMixinBase):
    """
    Import mixin.

    This is intended to be mixed with django.contrib.admin.ModelAdmin
    https://docs.djangoproject.com/en/dev/ref/contrib/admin/
    """

    #: template for change_list view
    import_export_change_list_template = 'admin/import_export/change_list_import.html'
    #: template for import view
    import_template_name = 'admin/import_export/import.html'
    #: available import formats
    formats = DEFAULT_FORMATS
    #: form class to use for the initial import step
    import_form_class = ImportForm
    #: form class to use for the confirm import step
    confirm_form_class = ConfirmImportForm
    #: import data encoding
    from_encoding = "utf-8-sig"
    skip_admin_log = None
    # storage class for saving temporary files
    tmp_storage_class = None

    def get_skip_admin_log(self):
        if self.skip_admin_log is None:
            return getattr(settings, 'IMPORT_EXPORT_SKIP_ADMIN_LOG', False)
        else:
            return self.skip_admin_log

    def get_tmp_storage_class(self):
        if self.tmp_storage_class is None:
            tmp_storage_class = getattr(
                settings, 'IMPORT_EXPORT_TMP_STORAGE_CLASS', TempFolderStorage,
            )
        else:
            tmp_storage_class = self.tmp_storage_class

        if isinstance(tmp_storage_class, str):
            tmp_storage_class = import_string(tmp_storage_class)
        return tmp_storage_class

    def has_import_permission(self, request):
        """
        Returns whether a request has import permission.
        """
        IMPORT_PERMISSION_CODE = getattr(settings, 'IMPORT_EXPORT_IMPORT_PERMISSION_CODE', None)
        if IMPORT_PERMISSION_CODE is None:
            return True

        opts = self.opts
        codename = get_permission_codename(IMPORT_PERMISSION_CODE, opts)
        return request.user.has_perm("%s.%s" % (opts.app_label, codename))

    def get_urls(self):
        urls = super().get_urls()
        info = self.get_model_info()
        my_urls = [
            path('process_import/',
                self.admin_site.admin_view(self.process_import),
                name='%s_%s_process_import' % info),
            path('import/',
                self.admin_site.admin_view(self.import_action),
                name='%s_%s_import' % info),
        ]
        return my_urls + urls

    @method_decorator(require_POST)
    def process_import(self, request, *args, **kwargs):
        """
        Perform the actual import action (after the user has confirmed the import)
        """
        if not self.has_import_permission(request):
            raise PermissionDenied

        if getattr(self.get_confirm_import_form, 'is_original', False):
            confirm_form = self.create_confirm_form(request)
        else:
            form_type = self.get_confirm_import_form()
            confirm_form = form_type(request.POST)

        if confirm_form.is_valid():
            import_formats = self.get_import_formats()
            input_format = import_formats[
                int(confirm_form.cleaned_data['input_format'])
            ](encoding=self.from_encoding)
            encoding = None if input_format.is_binary() else self.from_encoding
            tmp_storage_cls = self.get_tmp_storage_class()
            tmp_storage = tmp_storage_cls(
                name=confirm_form.cleaned_data['import_file_name'],
                encoding=encoding,
                read_mode=input_format.get_read_mode()
            )

            data = tmp_storage.read()
            dataset = input_format.create_dataset(data)
            result = self.process_dataset(dataset, confirm_form, request, *args, **kwargs)

            tmp_storage.remove()

            return self.process_result(result, request)

    def process_dataset(self, dataset, confirm_form, request, *args, **kwargs):

        res_kwargs = self.get_import_resource_kwargs(request, form=confirm_form, *args, **kwargs)
        resource = self.choose_import_resource_class(confirm_form)(**res_kwargs)

        imp_kwargs = self.get_import_data_kwargs(request, form=confirm_form, *args, **kwargs)
        return resource.import_data(dataset,
                                    dry_run=False,
                                    raise_errors=True,
                                    file_name=confirm_form.cleaned_data['original_file_name'],
                                    user=request.user,
                                    **imp_kwargs)

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

    @original
    def get_import_form(self):
        """
        .. deprecated:: 3.0
            Use :meth:`~import_export.admin.ImportMixin.get_import_form_class` or set the new
            :attr:`~import_export.admin.ImportMixin.import_form_class` attribute.
        """
        warnings.warn(
            "ImportMixin.get_import_form() is deprecated and will be removed in "
            "a future release. Please use get_import_form_class() instead.",
            category=DeprecationWarning
        )
        return self.import_form_class

    @original
    def get_confirm_import_form(self):
        """
        .. deprecated:: 3.0
            Use :func:`~import_export.admin.ImportMixin.get_confirm_form_class` or set the new
            :attr:`~import_export.admin.ImportMixin.confirm_form_class` attribute.
        """
        warnings.warn(
            "ImportMixin.get_confirm_import_form() is deprecated and will be removed in "
            "a future release. Please use get_confirm_form_class() instead.",
            category=DeprecationWarning
        )
        return self.confirm_form_class

    @original
    def get_form_kwargs(self, form, *args, **kwargs):
        """
        .. deprecated:: 3.0
            Use :meth:`~import_export.admin.ImportMixin.get_import_form_kwargs` or
            :meth:`~import_export.admin.ImportMixin.get_confirm_form_kwargs`
            instead, depending on which form you wish to customise.
        """
        warnings.warn(
            "ImportMixin.get_form_kwargs() is deprecated and will be removed "
            "in a future release. Please use get_import_form_kwargs() or "
            "get_confirm_form_kwargs() instead.",
            category=DeprecationWarning
        )
        return kwargs

    def create_import_form(self, request):
        """
        .. versionadded:: 3.0

        Return a form instance to use for the 'initial' import step.
        This method can be extended to make dynamic form updates to the
        form after it has been instantiated. You might also look to
        override the following:

        * :meth:`~import_export.admin.ImportMixin.get_import_form_class`
        * :meth:`~import_export.admin.ImportMixin.get_import_form_kwargs`
        * :meth:`~import_export.admin.ImportMixin.get_import_form_initial`
        * :meth:`~import_export.mixins.BaseImportMixin.get_import_resource_classes`
        """
        formats = self.get_import_formats()
        form_class = self.get_import_form_class(request)
        kwargs = self.get_import_form_kwargs(request)

        if not issubclass(form_class, ImportExportFormBase):
            warnings.warn(
                "The ImportForm class must inherit from ImportExportFormBase, "
                "this is needed for multiple resource classes to work properly. ",
                category=DeprecationWarning
            )
            return form_class(formats, **kwargs)
        return form_class(formats, self.get_import_resource_classes(), **kwargs)

    def get_import_form_class(self, request):
        """
        .. versionadded:: 3.0

        Return the form class to use for the 'import' step. If you only have
        a single custom form class, you can set the ``import_form_class``
        attribute to change this for your subclass.
        """
        # TODO: Remove following conditional when get_import_form() is removed
        if not getattr(self.get_import_form, 'is_original', False):
            warnings.warn(
                "ImportMixin.get_import_form() is deprecated and will be "
                "removed in a future release. Please use the new "
                "'import_form_class' attribute to specify a custom form "
                "class, or override the get_import_form_class() method if "
                "your requirements are more complex.",
                category=DeprecationWarning
            )
            return self.get_import_form()
        # Return the class attribute value
        return self.import_form_class

    def get_import_form_kwargs(self, request):
        """
        .. versionadded:: 3.0

        Return a dictionary of values with which to initialize the 'import'
        form (including the initial values returned by
        :meth:`~import_export.admin.ImportMixin.get_import_form_initial`).
        """
        return {
            "data": request.POST or None,
            "files": request.FILES or None,
            "initial": self.get_import_form_initial(request),
        }

    def get_import_form_initial(self, request):
        """
        .. versionadded:: 3.0

        Return a dictionary of initial field values to be provided to the
        'import' form.
        """
        return {}

    def create_confirm_form(self, request, import_form=None):
        """
        .. versionadded:: 3.0

        Return a form instance to use for the 'confirm' import step.
        This method can be extended to make dynamic form updates to the
        form after it has been instantiated. You might also look to
        override the following:

        * :meth:`~import_export.admin.ImportMixin.get_confirm_form_class`
        * :meth:`~import_export.admin.ImportMixin.get_confirm_form_kwargs`
        * :meth:`~import_export.admin.ImportMixin.get_confirm_form_initial`
        """
        form_class = self.get_confirm_form_class(request)
        kwargs = self.get_confirm_form_kwargs(request, import_form)
        return form_class(**kwargs)

    def get_confirm_form_class(self, request):
        """
        .. versionadded:: 3.0

        Return the form class to use for the 'confirm' import step. If you only
        have a single custom form class, you can set the ``confirm_form_class``
        attribute to change this for your subclass.
        """
        # TODO: Remove following conditional when get_confirm_import_form() is removed
        if not getattr(self.get_confirm_import_form, 'is_original', False):
            warnings.warn(
                "ImportMixin.get_confirm_import_form() is deprecated and will "
                "be removed in a future release. Please use the new "
                "'confirm_form_class' attribute to specify a custom form "
                "class, or override the get_confirm_form_class() method if "
                "your requirements are more complex.",
                category=DeprecationWarning
            )
            return self.get_confirm_import_form()
        # Return the class attribute value
        return self.confirm_form_class

    def get_confirm_form_kwargs(self, request, import_form=None):
        """
        .. versionadded:: 3.0

        Return a dictionary of values with which to initialize the 'confirm'
        form (including the initial values returned by
        :meth:`~import_export.admin.ImportMixin.get_confirm_form_initial`).
        """
        if import_form:
            # When initiated from `import_action()`, the 'posted' data
            # is for the 'import' form, not this one.
            data = None
            files = None
        else:
            data = request.POST or None
            files = request.FILES or None

        return {
            "data": data,
            "files": files,
            "initial": self.get_confirm_form_initial(request, import_form),
        }

    def get_confirm_form_initial(self, request, import_form):
        """
        .. versionadded:: 3.0

        Return a dictionary of initial field values to be provided to the
        'confirm' form.
        """
        if import_form is None:
            return {}
        return {
            'import_file_name': import_form.cleaned_data["import_file"].tmp_storage_name,
            'original_file_name': import_form.cleaned_data["import_file"].name,
            'input_format': import_form.cleaned_data["input_format"],
            'resource': import_form.cleaned_data.get("resource", ""),
        }

    def get_import_data_kwargs(self, request, *args, **kwargs):
        """
        Prepare kwargs for import_data.
        """
        form = kwargs.get('form')
        if form:
            kwargs.pop('form')
            return kwargs
        return {}

    def write_to_tmp_storage(self, import_file, input_format):
        encoding = None
        if not input_format.is_binary():
            encoding = self.from_encoding

        tmp_storage_cls = self.get_tmp_storage_class()
        tmp_storage = tmp_storage_cls(encoding=encoding, read_mode=input_format.get_read_mode())
        data = bytes()
        for chunk in import_file.chunks():
            data += chunk

        if tmp_storage_cls == MediaStorage and not input_format.is_binary():
            data = data.decode(self.from_encoding)

        tmp_storage.save(data)
        return tmp_storage

    def import_action(self, request, *args, **kwargs):
        """
        Perform a dry_run of the import to make sure the import will not
        result in errors.  If there are no errors, save the user
        uploaded file to a local temp file that will be used by
        'process_import' for the actual import.
        """
        if not self.has_import_permission(request):
            raise PermissionDenied

        context = self.get_import_context_data()

        import_formats = self.get_import_formats()
        if getattr(self.get_form_kwargs, "is_original", False):
            # Use new API
            import_form = self.create_import_form(request)
        else:
            form_class = self.get_import_form_class(request)
            form_kwargs = self.get_form_kwargs(form_class, *args, **kwargs)

            if issubclass(form_class, ImportExportFormBase):
                import_form = form_class(
                    import_formats,
                    self.get_import_resource_classes(),
                    request.POST or None,
                    request.FILES or None,
                    **form_kwargs
                )
            else:
                warnings.warn(
                    "The ImportForm class must inherit from ImportExportFormBase, "
                    "this is needed for multiple resource classes to work properly. ",
                    category=DeprecationWarning
                )
                import_form = form_class(
                    import_formats,
                    request.POST or None,
                    request.FILES or None,
                    **form_kwargs
                )

        resources = list()
        if request.POST and import_form.is_valid():
            input_format = import_formats[int(import_form.cleaned_data['input_format'])]()
            if not input_format.is_binary():
                input_format.encoding = self.from_encoding
            import_file = import_form.cleaned_data['import_file']
            # first always write the uploaded file to disk as it may be a
            # memory file or else based on settings upload handlers
            tmp_storage = self.write_to_tmp_storage(import_file, input_format)
            # allows get_confirm_form_initial() to include both the
            # original and saved file names from form.cleaned_data
            import_file.tmp_storage_name = tmp_storage.name

            try:
                # then read the file, using the proper format-specific mode
                # warning, big files may exceed memory
                data = tmp_storage.read()
                dataset = input_format.create_dataset(data)
            except Exception as e:
                import_form.add_error('import_file',
                               _(f"'{type(e).__name__}' encountered while trying to read file. "
                                 "Ensure you have chosen the correct format for the file. "
                                 f"{str(e)}"))

            if not import_form.errors:
                # prepare kwargs for import data, if needed
                res_kwargs = self.get_import_resource_kwargs(request, form=import_form, *args, **kwargs)
                resource = self.choose_import_resource_class(import_form)(**res_kwargs)
                resources = [resource]

                # prepare additional kwargs for import_data, if needed
                imp_kwargs = self.get_import_data_kwargs(request, form=import_form, *args, **kwargs)
                result = resource.import_data(dataset, dry_run=True,
                                              raise_errors=False,
                                              file_name=import_file.name,
                                              user=request.user,
                                              **imp_kwargs)

                context['result'] = result

                if not result.has_errors() and not result.has_validation_errors():
                    if getattr(self.get_form_kwargs, "is_original", False):
                        # Use new API
                        context["confirm_form"] = self.create_confirm_form(
                            request, import_form=import_form
                        )
                    else:
                        confirm_form_class = self.get_confirm_form_class(request)
                        initial = self.get_confirm_form_initial(request, import_form)
                        context["confirm_form"] = confirm_form_class(
                            initial=self.get_form_kwargs(form=import_form, **initial)
                        )
        else:
            res_kwargs = self.get_import_resource_kwargs(request, form=import_form, *args, **kwargs)
            resource_classes = self.get_import_resource_classes()
            resources = [resource_class(**res_kwargs) for resource_class in resource_classes]

        context.update(self.admin_site.each_context(request))

        context['title'] = _("Import")
        context['form'] = import_form
        context['opts'] = self.model._meta
        context['media'] = self.media + import_form.media
        context['fields_list'] = [
            (resource.get_display_name(), [f.column_name for f in resource.get_user_visible_fields()])
            for resource in resources
        ]

        request.current_app = self.admin_site.name
        return TemplateResponse(request, [self.import_template_name],
                                context)

    def changelist_view(self, request, extra_context=None):
        if extra_context is None:
            extra_context = {}
        extra_context['has_import_permission'] = self.has_import_permission(request)
        return super().changelist_view(request, extra_context)


class ExportMixin(BaseExportMixin, ImportExportMixinBase):
    """
    Export mixin.

    This is intended to be mixed with django.contrib.admin.ModelAdmin
    https://docs.djangoproject.com/en/dev/ref/contrib/admin/
    """
    #: template for change_list view
    import_export_change_list_template = 'admin/import_export/change_list_export.html'
    #: template for export view
    export_template_name = 'admin/import_export/export.html'
    #: export data encoding
    to_encoding = None
    #: form class to use for the initial import step
    export_form_class = ExportForm

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('export/',
                self.admin_site.admin_view(self.export_action),
                name='%s_%s_export' % self.get_model_info()),
        ]
        return my_urls + urls

    def has_export_permission(self, request):
        """
        Returns whether a request has export permission.
        """
        EXPORT_PERMISSION_CODE = getattr(settings, 'IMPORT_EXPORT_EXPORT_PERMISSION_CODE', None)
        if EXPORT_PERMISSION_CODE is None:
            return True

        opts = self.opts
        codename = get_permission_codename(EXPORT_PERMISSION_CODE, opts)
        return request.user.has_perm("%s.%s" % (opts.app_label, codename))

    def get_export_queryset(self, request):
        """
        Returns export queryset.

        Default implementation respects applied search and filters.
        """
        list_display = self.get_list_display(request)
        list_display_links = self.get_list_display_links(request, list_display)
        list_select_related = self.get_list_select_related(request)
        list_filter = self.get_list_filter(request)
        search_fields = self.get_search_fields(request)
        if self.get_actions(request):
            list_display = ['action_checkbox'] + list(list_display)

        ChangeList = self.get_changelist(request)
        changelist_kwargs = {
            'request': request,
            'model': self.model,
            'list_display': list_display,
            'list_display_links': list_display_links,
            'list_filter': list_filter,
            'date_hierarchy': self.date_hierarchy,
            'search_fields': search_fields,
            'list_select_related': list_select_related,
            'list_per_page': self.list_per_page,
            'list_max_show_all': self.list_max_show_all,
            'list_editable': self.list_editable,
            'model_admin': self,
        }
        changelist_kwargs['sortable_by'] = self.sortable_by
        if django.VERSION >= (4, 0):
            changelist_kwargs['search_help_text'] = self.search_help_text
        cl = ChangeList(**changelist_kwargs)

        return cl.get_queryset(request)

    def get_export_data(self, file_format, queryset, *args, **kwargs):
        """
        Returns file_format representation for given queryset.
        """
        request = kwargs.pop("request")
        if not self.has_export_permission(request):
            raise PermissionDenied

        data = self.get_data_for_export(request, queryset, *args, **kwargs)
        export_data = file_format.export_data(data)
        encoding = kwargs.get("encoding")
        if not file_format.is_binary() and encoding:
            export_data = export_data.encode(encoding)
        return export_data

    def get_export_context_data(self, **kwargs):
        return self.get_context_data(**kwargs)

    def get_context_data(self, **kwargs):
        return {}

    @original
    def get_export_form(self):
        """
        .. deprecated:: 3.0
            Use :meth:`~import_export.admin.ExportMixin.get_export_form_class` or set the new
            :attr:`~import_export.admin.ExportMixin.export_form_class` attribute.
        """
        warnings.warn(
            "ExportMixin.get_export_form() is deprecated and will "
            "be removed in a future release. Please use the new "
            "'export_form_class' attribute to specify a custom form "
            "class, or override the get_export_form_class() method if "
            "your requirements are more complex.",
            category=DeprecationWarning
        )
        return self.export_form_class

    def get_export_form_class(self):
        """
        Get the form class used to read the export format.
        """
        return self.export_form_class

    def export_action(self, request, *args, **kwargs):
        if not self.has_export_permission(request):
            raise PermissionDenied

        if getattr(self.get_export_form, 'is_original', False):
            form_type = self.get_export_form_class()
        else:
            form_type = self.get_export_form()
        formats = self.get_export_formats()
        form = form_type(formats, self.get_export_resource_classes(), request.POST or None)
        if form.is_valid():
            file_format = formats[
                int(form.cleaned_data['file_format'])
            ]()

            queryset = self.get_export_queryset(request)
            export_data = self.get_export_data(
                file_format, queryset, request=request, encoding=self.to_encoding, export_form=form,
            )
            content_type = file_format.get_content_type()
            response = HttpResponse(export_data, content_type=content_type)
            response['Content-Disposition'] = 'attachment; filename="%s"' % (
                self.get_export_filename(request, queryset, file_format),
            )

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

    def changelist_view(self, request, extra_context=None):
        if extra_context is None:
            extra_context = {}
        extra_context['has_export_permission'] = self.has_export_permission(request)
        return super().changelist_view(request, extra_context)

    def get_export_filename(self, request, queryset, file_format):
        return super().get_export_filename(file_format)


class ImportExportMixin(ImportMixin, ExportMixin):
    """
    Import and export mixin.
    """
    #: template for change_list view
    import_export_change_list_template = 'admin/import_export/change_list_import_export.html'


class ImportExportModelAdmin(ImportExportMixin, admin.ModelAdmin):
    """
    Subclass of ModelAdmin with import/export functionality.
    """


class ExportActionMixin(ExportMixin):
    """
    Mixin with export functionality implemented as an admin action.
    """

    # Don't use custom change list template.
    import_export_change_list_template = None

    def __init__(self, *args, **kwargs):
        """
        Adds a custom action form initialized with the available export
        formats.
        """
        choices = []
        formats = self.get_export_formats()
        if formats:
            for i, f in enumerate(formats):
                choices.append((str(i), f().get_title()))

        if len(formats) > 1:
            choices.insert(0, ('', '---'))

        self.action_form = export_action_form_factory(choices)
        super().__init__(*args, **kwargs)

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

            export_data = self.get_export_data(file_format, queryset, request=request, encoding=self.to_encoding)
            content_type = file_format.get_content_type()
            response = HttpResponse(export_data, content_type=content_type)
            response['Content-Disposition'] = 'attachment; filename="%s"' % (
                self.get_export_filename(request, queryset, file_format),
            )
            return response

    def get_actions(self, request):
        """
        Adds the export action to the list of available actions.
        """

        actions = super().get_actions(request)
        actions.update(
            export_admin_action=(
                ExportActionMixin.export_admin_action,
                "export_admin_action",
                _("Export selected %(verbose_name_plural)s"),
            )
        )
        return actions

    @property
    def media(self):
        super_media = super().media
        return forms.Media(js=super_media._js + ['import_export/action_formats.js'], css=super_media._css)


class ExportActionModelAdmin(ExportActionMixin, admin.ModelAdmin):
    """
    Subclass of ModelAdmin with export functionality implemented as an
    admin action.
    """


class ImportExportActionModelAdmin(ImportMixin, ExportActionModelAdmin):
    """
    Subclass of ExportActionModelAdmin with import/export functionality.
    Export functionality is implemented as an admin action.
    """
