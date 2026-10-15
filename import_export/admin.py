import logging
import os
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import admin, messages
from django.contrib.admin.models import ADDITION, CHANGE, DELETION, LogEntry
from django.contrib.auth import get_permission_codename
from django.core.exceptions import (
    FieldError,
    ImproperlyConfigured,
    PermissionDenied,
)
from django.core.paginator import Paginator
from django.forms import MultipleChoiceField, MultipleHiddenInput
from django.http import HttpResponse, HttpResponseRedirect, QueryDict
from django.shortcuts import render
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.decorators import method_decorator
from django.utils.module_loading import import_string
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from .constants import FORM_FIELD_PREFIX
from .formats.base_formats import get_binary_formats
from .forms import ConfirmImportForm, ImportForm, SelectableFieldsExportForm
from .mixins import BaseExportMixin, BaseImportMixin
from .results import RowResult
from .signals import post_export, post_import
from .tmp_storages import TempFolderStorage

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
        if getattr(self, "change_list_template", None):
            self.ie_base_change_list_template = self.change_list_template
        else:
            self.ie_base_change_list_template = "admin/change_list.html"

        try:
            self.change_list_template = getattr(
                self, "import_export_change_list_template", None
            )
        except AttributeError:
            logger.warning("failed to assign change_list_template attribute")

        if self.change_list_template is None:
            self.change_list_template = self.ie_base_change_list_template

    def get_model_info(self):
        app_label = self.model._meta.app_label
        return (app_label, self.model._meta.model_name)

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["ie_base_change_list_template"] = (
            self.ie_base_change_list_template
        )
        return super().changelist_view(request, extra_context)


class ImportMixin(BaseImportMixin, ImportExportMixinBase):
    """
    Import mixin.

    This is intended to be mixed with django.contrib.admin.ModelAdmin
    https://docs.djangoproject.com/en/dev/ref/contrib/admin/
    """

    #: template for change_list view
    import_export_change_list_template = "admin/import_export/change_list_import.html"
    #: template for import view
    import_template_name = "admin/import_export/import.html"
    #: form class to use for the initial import step
    import_form_class = ImportForm
    #: form class to use for the confirm import step
    confirm_form_class = ConfirmImportForm
    #: import data encoding
    from_encoding = "utf-8-sig"
    #: control which UI elements appear when import errors are displayed.
    #: Available options: 'message', 'row', 'traceback'
    import_error_display = ("message",)

    skip_admin_log = None
    # storage class for saving temporary files
    tmp_storage_class = None
    #: number of rows rendered per page of the import preview.
    #: Falls back to ``IMPORT_EXPORT_PREVIEW_PAGE_SIZE`` when ``None``.
    import_preview_page_size = None
    # session-key prefix for the GET-pagination metadata stash
    PAGINATION_SESSION_PREFIX = "django-import-export-preview-"

    def get_skip_admin_log(self):
        if self.skip_admin_log is None:
            return getattr(settings, "IMPORT_EXPORT_SKIP_ADMIN_LOG", False)
        else:
            return self.skip_admin_log

    def get_tmp_storage_class(self):
        if self.tmp_storage_class is None:
            tmp_storage_class = getattr(
                settings,
                "IMPORT_EXPORT_TMP_STORAGE_CLASS",
                TempFolderStorage,
            )
        else:
            tmp_storage_class = self.tmp_storage_class

        if isinstance(tmp_storage_class, str):
            tmp_storage_class = import_string(tmp_storage_class)
        return tmp_storage_class

    def get_tmp_storage_class_kwargs(self):
        """Override this method to provide additional kwargs to temp storage class."""
        return {}

    def has_import_permission(self, request):
        """
        Returns whether a request has import permission.
        """
        IMPORT_PERMISSION_CODE = getattr(
            settings, "IMPORT_EXPORT_IMPORT_PERMISSION_CODE", None
        )
        if IMPORT_PERMISSION_CODE is None:
            return True

        opts = self.opts
        codename = get_permission_codename(IMPORT_PERMISSION_CODE, opts)
        return request.user.has_perm(f"{opts.app_label}.{codename}")

    def get_urls(self):
        urls = super().get_urls()
        info = self.get_model_info()
        my_urls = [
            path(
                "process_import/",
                self.admin_site.admin_view(self.process_import),
                name="%s_%s_process_import" % info,
            ),
            path(
                "import/",
                self.admin_site.admin_view(self.import_action),
                name="%s_%s_import" % info,
            ),
        ]
        return my_urls + urls

    @method_decorator(require_POST)
    def process_import(self, request, **kwargs):
        """
        Perform the actual import action (after the user has confirmed the import)
        """
        if not self.has_import_permission(request):
            raise PermissionDenied

        confirm_form = self.create_confirm_form(request)
        if confirm_form.is_valid():
            import_formats = self.get_import_formats()
            input_format = import_formats[int(confirm_form.cleaned_data["format"])](
                encoding=self.from_encoding
            )
            encoding = None if input_format.is_binary() else self.from_encoding
            tmp_storage_cls = self.get_tmp_storage_class()
            tmp_storage = tmp_storage_cls(
                name=confirm_form.cleaned_data["import_file_name"],
                encoding=encoding,
                read_mode=input_format.get_read_mode(),
                **self.get_tmp_storage_class_kwargs(),
            )

            data = tmp_storage.read()
            dataset = input_format.create_dataset(data)
            result = self.process_dataset(dataset, confirm_form, request, **kwargs)

            tmp_storage.remove()
            self._drop_pagination_metadata(
                request, confirm_form.cleaned_data["import_file_name"]
            )

            return self.process_result(result, request)
        else:
            context = self.admin_site.each_context(request)
            context.update(
                {
                    "title": _("Import"),
                    "confirm_form": confirm_form,
                    "opts": self.model._meta,
                    "errors": confirm_form.errors,
                }
            )
            return TemplateResponse(request, [self.import_template_name], context)

    def process_dataset(
        self,
        dataset,
        form,
        request,
        **kwargs,
    ):
        # Get file_name from kwargs if provided, otherwise from form's cleaned_data
        # Must be extracted before passing kwargs to get_import_data_kwargs
        file_name = kwargs.pop("file_name", None)
        if file_name is None:
            file_name = form.cleaned_data.get("original_file_name")

        res_kwargs = self.get_import_resource_kwargs(request, form=form, **kwargs)
        resource = self.choose_import_resource_class(form, request)(**res_kwargs)
        imp_kwargs = self.get_import_data_kwargs(request=request, form=form, **kwargs)
        imp_kwargs["retain_instance_in_row_result"] = True

        return resource.import_data(
            dataset,
            dry_run=False,
            file_name=file_name,
            user=request.user,
            **imp_kwargs,
        )

    def process_result(self, result, request):
        self.generate_log_entries(result, request)
        self.add_success_message(result, request)
        post_import.send(sender=None, model=self.model)

        url = reverse(
            "admin:%s_%s_changelist" % self.get_model_info(),
            current_app=self.admin_site.name,
        )
        return HttpResponseRedirect(url)

    def generate_log_entries(self, result, request):
        if not self.get_skip_admin_log():
            self._log_actions(result, request)

    def add_success_message(self, result, request):
        opts = self.model._meta

        success_message = _(
            "Import finished: {} new, {} updated, {} deleted and {} skipped {}."
        ).format(
            result.totals[RowResult.IMPORT_TYPE_NEW],
            result.totals[RowResult.IMPORT_TYPE_UPDATE],
            result.totals[RowResult.IMPORT_TYPE_DELETE],
            result.totals[RowResult.IMPORT_TYPE_SKIP],
            opts.verbose_name_plural,
        )

        messages.success(request, success_message)

    def get_import_context_data(self, **kwargs):
        return self.get_context_data(**kwargs)

    def get_context_data(self, **kwargs):
        return {}

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

        return form_class(formats, self.get_import_resource_classes(request), **kwargs)

    def get_import_form_class(self, request):
        """
        .. versionadded:: 3.0

        Return the form class to use for the 'import' step. If you only have
        a single custom form class, you can set the ``import_form_class``
        attribute to change this for your subclass.
        """
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

        On the GET-side preview-pagination flow there is no uploaded file, so
        the storage-related values are read from the session entry written by
        the original POST. ``import_form`` is still a bound copy of the
        original upload form, so subclasses adding extra hidden fields to
        ``ConfirmImportForm`` can call ``super()`` and merge their own values
        from ``import_form.cleaned_data`` on both paths.
        """
        if import_form is None or self._is_preview_pagination_request(request):
            tmp_storage_name = os.path.basename(request.GET.get("import_file_name", ""))
            meta = self._get_pagination_metadata(request, tmp_storage_name)
            return {
                "import_file_name": meta.get("tmp_storage_name", tmp_storage_name),
                "original_file_name": meta.get("original_file_name", ""),
                "format": meta.get("format", ""),
                "resource": meta.get("resource", ""),
            }
        return {
            "import_file_name": import_form.cleaned_data[
                "import_file"
            ].tmp_storage_name,
            "original_file_name": import_form.cleaned_data["import_file"].name,
            "format": import_form.cleaned_data["format"],
            "resource": import_form.cleaned_data.get("resource", ""),
        }

    def get_import_data_kwargs(self, **kwargs):
        """
        Prepare kwargs for import_data.
        """
        form = kwargs.get("form")
        if form:
            kwargs.pop("form")
            return kwargs
        return kwargs

    def write_to_tmp_storage(self, import_file, input_format):
        encoding = None
        if not input_format.is_binary():
            encoding = self.from_encoding

        tmp_storage_cls = self.get_tmp_storage_class()
        tmp_storage = tmp_storage_cls(
            encoding=encoding,
            read_mode=input_format.get_read_mode(),
            **self.get_tmp_storage_class_kwargs(),
        )
        data = b""
        for chunk in import_file.chunks():
            data += chunk

        tmp_storage.save(data)
        return tmp_storage

    def add_data_read_fail_error_to_form(self, form, e):
        exc_name = repr(type(e).__name__)
        msg = _(
            "%(exc_name)s encountered while trying to read file. "
            "Ensure you have chosen the correct format for the file."
        ) % {"exc_name": exc_name}
        form.add_error("import_file", msg)

    def import_action(self, request, **kwargs):
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
        import_form = self.create_import_form(request)
        resources = []
        if request.POST and import_form.is_valid():
            input_format = import_formats[int(import_form.cleaned_data["format"])]()
            if not input_format.is_binary():
                input_format.encoding = self.from_encoding
            import_file = import_form.cleaned_data["import_file"]

            if self.is_skip_import_confirm_enabled():
                # This setting means we are going to skip the import confirmation step.
                # Go ahead and process the file for import in a transaction
                # If there are any errors, we roll back the transaction.
                # rollback_on_validation_errors is set to True so that we rollback on
                # validation errors. If this is not done validation errors would be
                # silently skipped.
                data = b""
                for chunk in import_file.chunks():
                    data += chunk
                try:
                    dataset = input_format.create_dataset(data)
                except Exception as e:
                    self.add_data_read_fail_error_to_form(import_form, e)
                if not import_form.errors:
                    result = self.process_dataset(
                        dataset,
                        import_form,
                        request,
                        raise_errors=False,
                        rollback_on_validation_errors=True,
                        file_name=import_file.name,
                        **kwargs,
                    )
                    if not result.has_errors() and not result.has_validation_errors():
                        return self.process_result(result, request)
                    else:
                        context["result"] = result
            else:
                # first always write the uploaded file to disk as it may be a
                # memory file or else based on settings upload handlers
                tmp_storage = self.write_to_tmp_storage(import_file, input_format)
                # allows get_confirm_form_initial() to include both the
                # original and saved file names from form.cleaned_data
                import_file.tmp_storage_name = tmp_storage.name
                # Stash original-upload metadata in the session so the GET
                # pagination handler can re-derive the dry-run without
                # round-tripping the original filename (PII) through the URL.
                self._save_pagination_metadata(
                    request,
                    tmp_storage.name,
                    original_file_name=import_file.name,
                    format_idx=import_form.cleaned_data["format"],
                    resource_idx=import_form.cleaned_data.get("resource", ""),
                )

                try:
                    # then read the file, using the proper format-specific mode
                    # warning, big files may exceed memory
                    data = tmp_storage.read()
                    dataset = input_format.create_dataset(data)
                except Exception as e:
                    self.add_data_read_fail_error_to_form(import_form, e)
                else:
                    if not dataset:
                        import_form.add_error(
                            "import_file",
                            _(
                                "No valid data to import. Ensure your file "
                                "has the correct headers or data for import."
                            ),
                        )

                if not import_form.errors:
                    # prepare kwargs for import data, if needed
                    res_kwargs = self.get_import_resource_kwargs(
                        request, form=import_form, **kwargs
                    )
                    resource = self.choose_import_resource_class(import_form, request)(
                        **res_kwargs
                    )
                    resources = [resource]

                    # prepare additional kwargs for import_data, if needed
                    imp_kwargs = self.get_import_data_kwargs(
                        request=request, form=import_form, **kwargs
                    )
                    result = resource.import_data(
                        dataset,
                        dry_run=True,
                        raise_errors=False,
                        file_name=import_file.name,
                        user=request.user,
                        **imp_kwargs,
                    )
                    context["result"] = result
                    context["preview_query_base"] = urlencode(
                        {"import_file_name": os.path.basename(tmp_storage.name)}
                    )

                    if not result.has_errors() and not result.has_validation_errors():
                        context["confirm_form"] = self.create_confirm_form(
                            request, import_form=import_form
                        )
        elif self._is_preview_pagination_request(request):
            resources = self._handle_preview_pagination_get(
                request, context, import_formats, kwargs
            )
        else:
            res_kwargs = self.get_import_resource_kwargs(
                request=request, form=import_form, **kwargs
            )
            resource_classes = self.get_import_resource_classes(request)
            resources = [
                resource_class(**res_kwargs) for resource_class in resource_classes
            ]

        if "result" in context:
            self._add_preview_pagination_context(request, context)

        context.update(self.admin_site.each_context(request))

        context["title"] = _("Import")
        context["form"] = import_form
        context["opts"] = self.model._meta
        context["media"] = self.media + import_form.media
        context["fields_list"] = [
            (
                resource.get_display_name(),
                [f.column_name for f in resource.get_user_visible_import_fields()],
            )
            for resource in resources
        ]
        context["import_error_display"] = self.import_error_display

        request.current_app = self.admin_site.name
        return TemplateResponse(request, [self.import_template_name], context)

    def get_import_preview_page_size(self):
        """
        .. versionadded:: 5.0

        Return the number of rows rendered per page of the import preview.

        Defaults to the ``import_preview_page_size`` attribute, falling back
        to the ``IMPORT_EXPORT_PREVIEW_PAGE_SIZE`` setting (``100``). Return
        ``None`` to disable pagination and render every preview row on a
        single page.
        """
        page_size = self.import_preview_page_size
        if page_size is None:
            page_size = getattr(settings, "IMPORT_EXPORT_PREVIEW_PAGE_SIZE", 100)
        if page_size is None:
            return None
        # bool is an int subclass, so reject it explicitly.
        if (
            isinstance(page_size, bool)
            or not isinstance(page_size, int)
            or page_size < 1
        ):
            raise ImproperlyConfigured(
                "IMPORT_EXPORT_PREVIEW_PAGE_SIZE must be a positive integer "
                f"or None, got {page_size!r}."
            )
        return page_size

    @staticmethod
    def _parse_non_negative_int(value, default=0):
        try:
            result = int(value)
        except (TypeError, ValueError):
            return default
        return result if result >= 0 else default

    def _pagination_session_key(self, tmp_storage_name):
        return (
            f"{self.PAGINATION_SESSION_PREFIX}"
            f"{os.path.basename(tmp_storage_name or '')}"
        )

    def _save_pagination_metadata(
        self,
        request,
        tmp_storage_name,
        *,
        original_file_name,
        format_idx,
        resource_idx,
    ):
        session = getattr(request, "session", None)
        if not tmp_storage_name or session is None:
            return
        session[self._pagination_session_key(tmp_storage_name)] = {
            # TempFolderStorage names are absolute paths, so keep the full
            # name here: only the basename travels in the URL.
            "tmp_storage_name": tmp_storage_name,
            "original_file_name": original_file_name,
            "format": format_idx,
            "resource": resource_idx,
            # The submitted form data (minus the uploaded file, which lives in
            # request.FILES), so that page navigation can rebuild a bound
            # ImportForm carrying any extra fields the subclass declared.
            "form_data": request.POST.urlencode(),
        }
        session.modified = True

    def _get_pagination_metadata(self, request, tmp_storage_name):
        session = getattr(request, "session", None)
        if not tmp_storage_name or session is None:
            return {}
        return session.get(self._pagination_session_key(tmp_storage_name), {})

    def _drop_pagination_metadata(self, request, tmp_storage_name):
        session = getattr(request, "session", None)
        if not tmp_storage_name or session is None:
            return
        session.pop(self._pagination_session_key(tmp_storage_name), None)
        session.modified = True

    def get_preview_result_for_pagination(
        self,
        resource,
        dataset,
        *,
        original_file_name="",
        **imp_kwargs,
    ):
        """
        .. versionadded:: 5.0

        Re-derive the dry-run :class:`~import_export.results.Result` for
        GET-side preview pagination. ``imp_kwargs`` is the dict returned
        by :meth:`~import_export.admin.ImportMixin.get_import_data_kwargs`
        for the request and so includes ``request`` if upstream hooks
        did not strip it. Override this to cache the Result keyed by the
        temporary-file name and avoid re-running the dry-run on every
        page click. The default implementation runs a full dry-run on
        each call.
        """
        request = imp_kwargs.get("request")
        user = request.user if request is not None else None
        return resource.import_data(
            dataset,
            dry_run=True,
            raise_errors=False,
            file_name=original_file_name,
            user=user,
            **imp_kwargs,
        )

    def _add_preview_pagination_context(self, request, context):
        # Paginate the dry-run preview so large imports do not render every
        # row at once, while still letting admins navigate every page. The
        # full Result is left untouched: confirm/process still imports every
        # row from the original tmp_storage file.
        page_size = self.get_import_preview_page_size()
        result = context["result"]
        # The errors / validation-errors / preview blocks in import.html are
        # mutually exclusive, so a single paginator over the active row set
        # is enough.
        if result.has_errors():
            rows = result.row_errors()
        elif result.has_validation_errors():
            rows = result.invalid_rows
        else:
            rows = result.valid_rows()
        if page_size is None or "preview_query_base" not in context:
            # Either pagination is switched off, or there is no tmp_storage
            # file to navigate back to (e.g. the skip-confirm flow rendering
            # errors) so there is nowhere for a "Next" link to point. Render
            # every row on a single page rather than hiding rows behind
            # unreachable navigation.
            page_size = max(len(rows), 1)
        paginator = Paginator(rows, page_size)
        page_number = (
            self._parse_non_negative_int(request.GET.get("page"), default=1) or 1
        )
        context["preview_page_size"] = page_size
        context["preview_page"] = paginator.get_page(page_number)

    def _is_preview_pagination_request(self, request):
        if request.method != "GET":
            return False
        if "page" not in request.GET:
            return False
        return "import_file_name" in request.GET

    def _preview_unavailable(self, request, reason, exc_info=False):
        # The preview cannot be re-derived (expired session, missing or
        # unreadable temporary file, stale metadata). import_action falls
        # back to rendering the plain upload form, so tell the user why.
        logger.debug(
            "import preview pagination unavailable: %s", reason, exc_info=exc_info
        )
        messages.warning(
            request,
            _("The import preview has expired. Please upload the file again."),
        )
        return []

    def _handle_preview_pagination_get(self, request, context, import_formats, kwargs):
        # Re-derive the dry-run Result from the tmp_storage file written
        # during the original upload, so that GET-based page navigation
        # can render any preview page without re-uploading the file.
        tmp_storage_name = os.path.basename(request.GET.get("import_file_name", ""))
        if not tmp_storage_name:
            return self._preview_unavailable(request, "no import_file_name in query")

        metadata = self._get_pagination_metadata(request, tmp_storage_name)
        if not metadata:
            return self._preview_unavailable(request, "no session metadata")

        format_idx = self._parse_non_negative_int(metadata.get("format"), default=-1)
        if format_idx < 0 or format_idx >= len(import_formats):
            return self._preview_unavailable(request, "unknown import format")

        input_format = import_formats[format_idx]()
        if not input_format.is_binary():
            input_format.encoding = self.from_encoding
        encoding = None if input_format.is_binary() else self.from_encoding

        tmp_storage_cls = self.get_tmp_storage_class()
        tmp_storage = tmp_storage_cls(
            name=metadata.get("tmp_storage_name", tmp_storage_name),
            encoding=encoding,
            read_mode=input_format.get_read_mode(),
            **self.get_tmp_storage_class_kwargs(),
        )
        try:
            data = tmp_storage.read()
            dataset = input_format.create_dataset(data)
        except Exception:
            return self._preview_unavailable(
                request, "temporary file could not be read", exc_info=True
            )

        resource_classes = self.get_import_resource_classes(request)
        resource_idx_str = str(metadata.get("resource") or "")
        if resource_idx_str:
            resource_idx = self._parse_non_negative_int(resource_idx_str, default=-1)
            if resource_idx < 0 or resource_idx >= len(resource_classes):
                return self._preview_unavailable(request, "unknown resource index")

        # Rebuild an ImportForm bound to the same data the original upload
        # POSTed, so subclasses' extension hooks (choose_import_resource_class,
        # get_import_resource_kwargs, get_import_data_kwargs,
        # get_confirm_form_initial) see the same form they do on the POST
        # path, including any extra fields the subclass declared.
        form_class = self.get_import_form_class(request)
        pagination_form = form_class(
            self.get_import_formats(),
            resource_classes,
            data=QueryDict(metadata.get("form_data", "")),
        )
        # There is no uploaded file on a GET, so the form is never valid.
        # Clean it anyway: Django still populates cleaned_data for every
        # field which did validate, which is what the hooks above read.
        pagination_form.is_valid()

        res_kwargs = self.get_import_resource_kwargs(
            request, form=pagination_form, **kwargs
        )
        resource = self.choose_import_resource_class(pagination_form, request)(
            **res_kwargs
        )

        imp_kwargs = self.get_import_data_kwargs(
            request=request, form=pagination_form, **kwargs
        )
        original_file_name = metadata.get("original_file_name", "")
        result = self.get_preview_result_for_pagination(
            resource,
            dataset,
            original_file_name=original_file_name,
            **imp_kwargs,
        )
        context["result"] = result
        context["preview_query_base"] = urlencode(
            {"import_file_name": os.path.basename(tmp_storage.name)}
        )

        if not result.has_errors() and not result.has_validation_errors():
            context["confirm_form"] = self.create_confirm_form(
                request, import_form=pagination_form
            )

        return [resource]

    def changelist_view(self, request, extra_context=None):
        if extra_context is None:
            extra_context = {}
        extra_context["has_import_permission"] = self.has_import_permission(request)
        return super().changelist_view(request, extra_context)

    def _log_actions(self, result, request):
        """
        Create appropriate LogEntry instances for the result.
        """
        rows = {}
        for row in result:
            rows.setdefault(row.import_type, [])
            rows[row.import_type].append(row.instance)

        self._create_log_entries(request.user.pk, rows)

    def _create_log_entries(self, user_pk, rows):
        logentry_map = {
            RowResult.IMPORT_TYPE_NEW: ADDITION,
            RowResult.IMPORT_TYPE_UPDATE: CHANGE,
            RowResult.IMPORT_TYPE_DELETE: DELETION,
        }
        missing = object()
        for import_type, instances in rows.items():
            action_flag = logentry_map.get(import_type, missing)
            if action_flag is not missing:
                self._create_log_entry(
                    user_pk, rows[import_type], import_type, action_flag
                )

    def _create_log_entry(self, user_pk, rows, import_type, action_flag):
        if len(rows) > 0:
            LogEntry.objects.log_actions(
                user_pk,
                rows,
                action_flag,
                change_message=_("%s through import_export" % import_type),
                single_object=len(rows) == 1,
            )


class ExportMixin(BaseExportMixin, ImportExportMixinBase):
    """
    Export mixin.

    This is intended to be mixed with
    `ModelAdmin <https://docs.djangoproject.com/en/stable/ref/contrib/admin/>`_.
    """

    #: template for change_list view
    import_export_change_list_template = "admin/import_export/change_list_export.html"
    #: template for export view
    export_template_name = "admin/import_export/export.html"
    #: export data encoding
    to_encoding = None
    #: Form class to use for the initial export step.
    #: Assign to :class:`~import_export.forms.ExportForm` if you would
    #: like to disable selectable fields feature.
    export_form_class = SelectableFieldsExportForm

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path(
                "export/",
                self.admin_site.admin_view(self.export_action),
                name="%s_%s_export" % self.get_model_info(),
            ),
        ]
        return my_urls + urls

    def has_export_permission(self, request):
        """
        Returns whether a request has export permission.
        """
        EXPORT_PERMISSION_CODE = getattr(
            settings, "IMPORT_EXPORT_EXPORT_PERMISSION_CODE", None
        )
        if EXPORT_PERMISSION_CODE is None:
            return True

        opts = self.opts
        codename = get_permission_codename(EXPORT_PERMISSION_CODE, opts)
        return request.user.has_perm(f"{opts.app_label}.{codename}")

    def get_export_queryset(self, request):
        """
        Returns export queryset. The queryset is obtained by calling
        ModelAdmin
        `get_queryset()
        <https://docs.djangoproject.com/en/dev/ref/contrib/admin/#django.contrib.admin.ModelAdmin.get_queryset>`_.

        Default implementation respects applied search and filters.
        """
        list_display = self.get_list_display(request)
        list_display_links = self.get_list_display_links(request, list_display)
        list_select_related = self.get_list_select_related(request)
        list_filter = self.get_list_filter(request)
        search_fields = self.get_search_fields(request)
        if self.get_actions(request):
            list_display = ["action_checkbox"] + list(list_display)

        ChangeList = self.get_changelist(request)
        changelist_kwargs = {
            "request": request,
            "model": self.model,
            "list_display": list_display,
            "list_display_links": list_display_links,
            "list_filter": list_filter,
            "date_hierarchy": self.date_hierarchy,
            "search_fields": search_fields,
            "list_select_related": list_select_related,
            "list_per_page": self.list_per_page,
            "list_max_show_all": self.list_max_show_all,
            "list_editable": self.list_editable,
            "model_admin": self,
            "sortable_by": self.sortable_by,
        }
        changelist_kwargs["search_help_text"] = self.search_help_text

        class ExportChangeList(ChangeList):
            def get_filters_params(self, params=None):
                """Strip params not intended as queryset filters.

                ``_changelist_filters`` is added by Django to change-view URLs
                when the user navigated there from a filtered changelist.  It is
                not a model field lookup and must be ignored, otherwise
                ``ChangeList`` raises ``IncorrectLookupParameters``.
                """
                result = super().get_filters_params(params)
                result.pop("_changelist_filters", None)
                return result

            def get_results(self, request):
                """
                Overrides ChangeList.get_results() to bypass default operations like
                pagination and result counting, which are not needed for export. This
                prevents executing unnecessary COUNT queries during ChangeList
                initialization.
                """
                pass

        cl = ExportChangeList(**changelist_kwargs)

        # get_queryset() is already called during initialization,
        # it is enough to get its results
        if hasattr(cl, "queryset"):
            return cl.queryset

        # Fallback in case the ChangeList doesn't have queryset attribute set
        return cl.get_queryset(request)

    def get_export_data(self, file_format, request, queryset, **kwargs):
        """
        Returns file_format representation for given queryset.
        """
        if not self.has_export_permission(request):
            raise PermissionDenied

        force_native_type = type(file_format) in get_binary_formats()
        data = self.get_data_for_export(
            request,
            queryset,
            force_native_type=force_native_type,
            **kwargs,
        )
        export_data = file_format.export_data(data)
        encoding = kwargs.get("encoding")
        if not file_format.is_binary() and encoding:
            export_data = export_data.encode(encoding)
        return export_data

    def get_export_context_data(self, **kwargs):
        return self.get_context_data(**kwargs)

    def get_context_data(self, **kwargs):
        return {}

    def get_export_form_class(self):
        """
        Get the form class used to read the export format.
        """
        return self.export_form_class

    def export_action(self, request):
        """
        Handles the default workflow for both the export form and the
        export of data to file.
        """
        if not self.has_export_permission(request):
            raise PermissionDenied

        form_type = self.get_export_form_class()
        formats = self.get_export_formats()
        queryset = self.get_export_queryset(request)
        # only skip the form for a direct export (e.g. the changelist 'Export'
        # button) - a POST carries data from the export form rendered by the
        # action flow, and must be processed as a form submission
        if self.is_skip_export_form_enabled() and not request.POST:
            response = self._do_file_export(formats[0](), request, queryset)
            if response is not None:
                return response
            # on export error, redirect back to the changelist with the
            # error message rather than rendering the skipped export form
            changelist_url = reverse(
                "%s:%s_%s_changelist"
                % (
                    self.admin_site.name,
                    self.model._meta.app_label,
                    self.model._meta.model_name,
                )
            )
            return HttpResponseRedirect(changelist_url)

        form = form_type(
            formats,
            self.get_export_resource_classes(request),
            data=request.POST or None,
        )
        if request.POST and f"{FORM_FIELD_PREFIX}export_items" in request.POST:
            # this field is instantiated if the export is POSTed from the
            # 'action' drop down
            form.fields["export_items"] = MultipleChoiceField(
                widget=MultipleHiddenInput,
                required=False,
                choices=[(pk, pk) for pk in queryset.values_list("pk", flat=True)],
            )
        if form.is_valid():
            file_format = formats[int(form.cleaned_data["format"])]()

            if "export_items" in form.changed_data:
                # this request has arisen from an Admin UI action
                # export item pks are stored in form data
                # so generate the queryset from the stored pks
                queryset = queryset.filter(pk__in=form.cleaned_data["export_items"])

            response = self._do_file_export(
                file_format, request, queryset, export_form=form
            )
            if response is not None:
                return response

        context = self.init_request_context_data(request, form)
        request.current_app = self.admin_site.name
        return TemplateResponse(request, [self.export_template_name], context=context)

    def changelist_view(self, request, extra_context=None):
        if extra_context is None:
            extra_context = {}
        extra_context["has_export_permission"] = self.has_export_permission(request)
        return super().changelist_view(request, extra_context)

    def get_export_filename(self, request, queryset, file_format):
        return super().get_export_filename(file_format)

    def init_request_context_data(self, request, form):
        context = self.get_export_context_data()
        context.update(self.admin_site.each_context(request))
        context["title"] = _("Export")
        context["form"] = form
        context["opts"] = self.model._meta
        context["fields_list"] = [
            (
                res.get_display_name(),
                [
                    field.column_name
                    for field in res(
                        **self.get_export_resource_kwargs(request)
                    ).get_user_visible_export_fields()
                ],
            )
            for res in self.get_export_resource_classes(request)
        ]
        return context

    def _do_file_export(self, file_format, request, queryset, export_form=None):
        """
        Export the queryset to file and return the file response.
        Returns ``None`` if the export failed with a ``ValueError`` or
        ``FieldError`` (issue #1723) - the error is added to ``messages``
        and the caller decides which page to render.
        """
        try:
            export_data = self.get_export_data(
                file_format,
                request,
                queryset,
                encoding=self.to_encoding,
                export_form=export_form,
            )
        except (ValueError, FieldError) as e:
            messages.error(request, str(e))
            return None
        content_type = file_format.get_content_type()
        response = HttpResponse(export_data, content_type=content_type)
        response["Content-Disposition"] = 'attachment; filename="{}"'.format(
            self.get_export_filename(request, queryset, file_format),
        )
        post_export.send(sender=None, model=self.model)
        return response


class ImportExportMixin(ImportMixin, ExportMixin):
    """
    Import and export mixin.
    """

    #: template for change_list view
    import_export_change_list_template = (
        "admin/import_export/change_list_import_export.html"
    )


class ImportExportModelAdmin(ImportExportMixin, admin.ModelAdmin):
    """
    Subclass of ModelAdmin with import/export functionality.
    """


class ExportActionMixin(ExportMixin):
    """
    Mixin with export functionality implemented as an admin action.
    """

    #: template for change form
    change_form_template = "admin/import_export/change_form.html"

    #: Flag to indicate whether to show 'export' button on change form
    show_change_form_export = True

    # This action will receive a selection of items as a queryset,
    # store them in the context, and then render the 'export' admin form page,
    # so that users can select file format and resource

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}
        extra_context["show_change_form_export"] = (
            self.show_change_form_export and self.has_export_permission(request)
        )
        return super().change_view(
            request,
            object_id,
            form_url,
            extra_context=extra_context,
        )

    def response_change(self, request, obj):
        # called if the export is triggered from the instance detail page.
        if "_export-item" in request.POST:
            return self.export_admin_action(
                request, self.model.objects.filter(pk=obj.pk)
            )
        return super().response_change(request, obj)

    def export_admin_action(self, request, queryset):
        """
        Action runs on POST from instance action menu (if enabled).
        """
        formats = self.get_export_formats()
        # Honor both skip flags so IMPORT_EXPORT_SKIP_ADMIN_EXPORT_UI /
        # skip_export_form also skip the action and change-form confirm UI,
        # matching the documented behaviour.
        if (
            self.is_skip_export_form_from_action_enabled()
            or self.is_skip_export_form_enabled()
        ):
            file_format = formats[0]()
            response = self._do_file_export(file_format, request, queryset)
            if response is not None:
                return response
            # on export error, redirect back to the originating page
            # (changelist or change form)
            return HttpResponseRedirect(request.get_full_path())

        form_type = self.get_export_form_class()
        formats = self.get_export_formats()
        export_items = list(queryset.values_list("pk", flat=True))
        form = form_type(
            formats=formats,
            resources=self.get_export_resource_classes(request),
            initial={"export_items": export_items},
        )
        # selected items are to be stored as a hidden input on the form
        form.fields["export_items"] = MultipleChoiceField(
            widget=MultipleHiddenInput, required=False, choices=export_items
        )
        context = self.init_request_context_data(request, form)

        # this is necessary to render the FORM action correctly
        # i.e. so the POST goes to the correct URL
        export_url = reverse(
            "%s:%s_%s_export"
            % (
                self.admin_site.name,
                self.model._meta.app_label,
                self.model._meta.model_name,
            )
        )

        # Preserve admin changelist filters by including request GET parameters
        # This fixes issue #2097 where applied filters are lost during export
        if request.GET:
            export_url += "?" + urlencode(request.GET)

        context["export_url"] = export_url

        return render(request, "admin/import_export/export.html", context=context)

    def get_actions(self, request):
        """
        Adds the export action to the list of available actions.
        """
        actions = super().get_actions(request)
        if self.has_export_permission(request):
            actions.update(
                export_admin_action=(
                    type(self).export_admin_action,
                    "export_admin_action",
                    _("Export selected %(verbose_name_plural)s"),
                )
            )
        return actions


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
