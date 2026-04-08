import logging

from django.conf import settings
from django.utils.timezone import now

from . import constants
from .formats import base_formats
from .forms import SelectableFieldsExportForm
from .resources import modelresource_factory

logger = logging.getLogger(__name__)


class BaseImportExportMixin:
    """
    Base mixin for functionality related to importing and exporting via the Admin
    interface.
    """

    resource_classes = []

    @property
    def formats(self):
        return base_formats.get_default_formats()

    @property
    def export_formats(self):
        return getattr(settings, "EXPORT_FORMATS", self.formats)

    @property
    def import_formats(self):
        return getattr(settings, "IMPORT_FORMATS", self.formats)

    def check_resource_classes(self, resource_classes):
        if resource_classes and not hasattr(resource_classes, "__getitem__"):
            raise Exception(
                "The resource_classes field type must be "
                "subscriptable (list, tuple, ...)"
            )

    def get_resource_classes(self, request):
        """
        Return subscriptable type (list, tuple, ...) containing resource classes
        :param request: The request object.
        :returns: The Resource classes.
        """
        if not self.resource_classes:
            return [modelresource_factory(self.model)]
        return self.resource_classes

    def get_resource_kwargs(self, request, *args, **kwargs):
        """
        Return the kwargs which are to be passed to the Resource constructor.
        Can be overridden to provide additional kwarg params.

        :param request: The request object.
        :param kwargs: Keyword arguments.
        :returns: The Resource kwargs (by default, is the kwargs passed).
        """
        return kwargs

    def get_resource_index(self, form):
        """
        Return the index of the resource class defined in the form.

        :param form: The form object.
        :returns: The index of the resource as an int.
        """
        resource_index = 0
        prefix = constants.FORM_FIELD_PREFIX
        if form and f"{prefix}resource" in form.data:
            try:
                resource_index = int(form.data[f"{prefix}resource"])
            except ValueError:
                pass
        return resource_index


class BaseImportMixin(BaseImportExportMixin):
    #: If enabled, the import workflow skips the import confirm page
    #: and imports the data directly.
    #: See :ref:`import_export_skip_admin_confirm`.
    skip_import_confirm = False

    def get_import_resource_classes(self, request):
        """
        :param request: The request object.
        Returns ResourceClass subscriptable (list, tuple, ...) to use for import.
        """
        resource_classes = self.get_resource_classes(request)
        self.check_resource_classes(resource_classes)
        return resource_classes

    def get_import_formats(self):
        """
        Returns available import formats.
        """
        return [f for f in self.import_formats if f().can_import()]

    def get_import_resource_kwargs(self, request, **kwargs):
        """
        Returns kwargs which will be passed to the Resource constructor.
        :param request: The request object.
        :param kwargs: Keyword arguments.
        :returns: The kwargs (dict)
        """
        return self.get_resource_kwargs(request, **kwargs)

    def choose_import_resource_class(self, form, request):
        """
        Identify which class should be used for import
        :param form: The form object.
        :param request: The request object.
        :returns: The import Resource class.
        """
        resource_index = self.get_resource_index(form)
        return self.get_import_resource_classes(request)[resource_index]

    def is_skip_import_confirm_enabled(self):
        return (
            getattr(settings, "IMPORT_EXPORT_SKIP_ADMIN_CONFIRM", False)
            or self.skip_import_confirm is True
        )


class BaseExportMixin(BaseImportExportMixin):
    model = None

    #: If enabled, the export workflow skips the export form and
    #: exports the data directly.
    #: See :ref:`import_export_skip_admin_export_ui`.
    skip_export_form = False

    #: If enabled, the export workflow from Admin UI action menu
    #: skips the export form and exports the data directly.
    #: See :ref:`import_export_skip_admin_action_export_ui`.
    skip_export_form_from_action = False

    def get_export_formats(self):
        """
        Returns available export formats.
        """
        return [f for f in self.export_formats if f().can_export()]

    def get_export_resource_classes(self, request):
        """
        Returns ResourceClass subscriptable (list, tuple, ...) to use for export.
        :param request: The request object.
        :returns: The Resource classes.
        """
        resource_classes = self.get_resource_classes(request)
        self.check_resource_classes(resource_classes)
        return resource_classes

    def choose_export_resource_class(self, form, request):
        """
        Identify which class should be used for export
        :param request: The request object.
        :param form: The form object.
        :returns: The export Resource class.
        """
        resource_index = self.get_resource_index(form)
        return self.get_export_resource_classes(request)[resource_index]

    def get_export_resource_kwargs(self, request, **kwargs):
        """
        Returns kwargs which will be passed to the Resource constructor.
        :param request: The request object.
        :param kwargs: Keyword arguments.
        :returns: The kwargs (dict)
        """
        return self.get_resource_kwargs(request, **kwargs)

    def get_export_resource_fields_from_form(self, form):
        if isinstance(form, SelectableFieldsExportForm):
            export_fields = form.get_selected_resource_export_fields()
            if export_fields:
                return export_fields

        return

    def get_data_for_export(self, request, queryset, **kwargs):
        export_form = kwargs.get("export_form")
        export_class = self.choose_export_resource_class(export_form, request)
        export_resource_kwargs = self.get_export_resource_kwargs(request, **kwargs)
        export_fields = self.get_export_resource_fields_from_form(export_form)
        cls = export_class(**export_resource_kwargs)
        export_data = cls.export(
            queryset=queryset, export_fields=export_fields, **kwargs
        )
        return export_data

    def get_export_filename(self, file_format):
        date_str = now().strftime("%Y-%m-%d")
        filename = "{}-{}.{}".format(
            self.model.__name__,
            date_str,
            file_format.get_extension(),
        )
        return filename

    def is_skip_export_form_enabled(self):
        return (
            getattr(settings, "IMPORT_EXPORT_SKIP_ADMIN_EXPORT_UI", False)
            or self.skip_export_form is True
        )

    def is_skip_export_form_from_action_enabled(self):
        return (
            getattr(settings, "IMPORT_EXPORT_SKIP_ADMIN_ACTION_EXPORT_UI", False)
            or self.skip_export_form_from_action is True
        )
