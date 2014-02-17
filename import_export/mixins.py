from __future__ import unicode_literals
from __future__ import absolute_import

import os
import tempfile

#from django.utils import six
from django.conf.urls import patterns, url
from django.core.exceptions import PermissionDenied
from django.template.response import TemplateResponse
from django.core.files.uploadedfile import UploadedFile

from rest_framework import generics
from rest_framework import mixins
from rest_framework import permissions, authentication
from rest_framework.settings import api_settings
from rest_framework.parsers import FileUploadParser
from rest_framework.request import Empty

from .forms import ImportForm, ConfirmImportForm

from rest_framework.response import Response
from rest_framework import status


class BaseView(object):
    modelAdmin = None
    export_template_name = 'admin/import_export/export.html'
    import_template_name = 'admin/import_export/import.html'

    # The following policies may be set at either globally, or per-view.
    renderer_classes = api_settings.DEFAULT_RENDERER_CLASSES
    parser_classes = api_settings.DEFAULT_PARSER_CLASSES
    throttle_classes = api_settings.DEFAULT_THROTTLE_CLASSES
    content_negotiation_class = api_settings.DEFAULT_CONTENT_NEGOTIATION_CLASS

    # FIXME redirect on 403?
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAdminUser,)


class ImportView(BaseView, generics.CreateAPIView):

    def get(self, request):
        context = {}

        form = ImportForm(request.POST or None,
                          request.FILES or None)

        serializer = self.get_serializer()

        context['opts'] = serializer.Meta.model._meta
        context['form'] = form
        context['fields'] = serializer.fields

        return TemplateResponse(request, [self.import_template_name],
                                context, current_app=self.modelAdmin.admin_site.name)

    def create(self, request, *args, **kwargs):
        context = {}
        results = []
        row_errors = []
        form = ImportForm(request.POST or None,
                          request.FILES or None)

        if form.is_valid():
            import_file = form.cleaned_data['import_file']

            # first always write the uploaded file to disk as it may be a
            # memory file or else based on settings upload handlers
            with tempfile.NamedTemporaryFile(delete=False) as uploaded_file:
                for chunk in import_file.chunks():
                    uploaded_file.write(chunk)

            parser = request.negotiator.select_parser(import_file, request.parsers)
            media_type = request.FILES['import_file'].content_type

            if not parser:
                raise request.exceptions.UnsupportedMediaType(media_type)

            parsed = parser.parse(import_file, media_type, request.parser_context)

            for row, data in enumerate(parsed):
                serializer = self.get_serializer(data=data)

                if serializer.is_valid():
                    results.append(serializer.data)
                else:
                    row_errors.append((row, serializer.errors))

        if not row_errors:
            context['results'] = results
            context['confirm_form'] = ConfirmImportForm(initial={
                'import_file_name': os.path.basename(uploaded_file.name),
                'import_file_mimetype': media_type,
            })

        serializer = get_serializer()

        context['opts'] = serializer.Meta.model._meta
        context['form'] = form
        context['fields'] = serializer.fields
        context['row_errors'] = row_errors

        return TemplateResponse(request, [self.import_template_name],
                                context, current_app=self.modelAdmin.admin_site.name)

class ImportConfirmView(BaseView, generics.CreateAPIView):

    def create(self, request, *args, **kwargs):
        context = {}
        row_errors = []
        form = ConfirmImportForm(request.POST or None,
                                 request.FILES or None)

        if form.is_valid():
            import_file_path = open(os.path.join(tempfile.gettempdir(),
                                            os.path.basename(form.cleaned_data['import_file_name'])))
            media_type = form.cleaned_data['import_file_mimetype']

            import_file = UploadedFile(file=import_file_path, content_type=media_type)

            parser = request.negotiator.select_parser(import_file, request.parsers)

            if not parser:
                raise request.exceptions.UnsupportedMediaType(media_type)

            parsed = parser.parse(import_file, media_type, request.parser_context)

            for row, data in enumerate(parsed):
                serializer = self.get_serializer(data=data)

                if serializer.is_valid():
                    try:
                        self.pre_save(serializer.object)
                        self.object = serializer.save(force_insert=True)
                        self.post_save(self.object, created=True)
                    except Exception as e:
                        row_errors.append((row, e))

            if not row_errors:
                return self.modelAdmin.response_post_save_change(request, None)

        serializer = self.get_serializer()

        context['opts'] = serializer.Meta.model._meta
        context['form'] = form
        context['fields'] = serializer.fields
        context['row_errors'] = row_errors

        return TemplateResponse(request, [self.import_template_name],
                                context, current_app=self.modelAdmin.admin_site.name)


class ExportView(BaseView, generics.ListAPIView):

    def list(self, request, *args, **kwargs):
        filter = None
        self.model = self.serializer_class.Meta.model

        self.object_list = self.filter_queryset(self.get_queryset())
        format_query_param = self.settings.URL_FORMAT_OVERRIDE

        if not request.QUERY_PARAMS.get(format_query_param):
            for backend in self.get_filter_backends():
                filter = backend().get_filter_class(self.modelAdmin, self.object_list)

            serializer = self.get_serializer()

            context = {
                'opts': serializer.Meta.model._meta,
                'format_query_param': format_query_param,
                'formats': [r.format for r in self.get_renderers()],
                'filter': filter,
            }

            return TemplateResponse(request, [self.export_template_name],
                                    context, current_app=self.modelAdmin.admin_site.name)



        # Default is to allow empty querysets.  This can be altered by setting
        # `.allow_empty = False`, to raise 404 errors on empty querysets.
        if not self.allow_empty and not self.object_list:
            warnings.warn(
                'The `allow_empty` parameter is due to be deprecated. '
                'To use `allow_empty=False` style behavior, You should override '
                '`get_queryset()` and explicitly raise a 404 on empty querysets.',
                PendingDeprecationWarning
            )
            class_name = self.__class__.__name__
            error_msg = self.empty_error % {'class_name': class_name}
            raise Http404(error_msg)

        # Switch between paginated or standard style responses
        page = self.paginate_queryset(self.object_list)
        if page is not None:
            serializer = self.get_pagination_serializer(page)
        else:
            serializer = self.get_serializer(self.object_list, many=True)

        (renderer, content_type) = self.perform_content_negotiation(request)

        return Response(renderer.render(serializer.data), content_type=content_type)


class ImportModelAdminMixin(BaseView):

    def get_urls(self):
        urls = super(ImportModelAdminMixin, self).get_urls()
        info = (self.serializer_class.Meta.model._meta.app_label,
                self.serializer_class.Meta.model._meta.module_name)

        new_urls = patterns(
            '',
            url(r'^process_import/$',
                self.admin_site.admin_view(ImportConfirmView.as_view(
                    serializer_class=self.serializer_class,
                    import_template_name=self.import_template_name,
                    modelAdmin=self)),
                name='%s_%s_process_import' % info),
            url(r'^import/$',
                self.admin_site.admin_view(ImportView.as_view(
                    serializer_class=self.serializer_class,
                    import_template_name=self.import_template_name,
                    modelAdmin=self)),
                name='%s_%s_import' % info),
        )
        return new_urls + urls


class ExportModelAdminMixin(BaseView):
    def get_urls(self):
        urls = super(ExportModelAdminMixin, self).get_urls()

        info = (self.serializer_class.Meta.model._meta.app_label,
                self.serializer_class.Meta.model._meta.module_name)

        new_urls = patterns(
            '',
            url(r'^export/$',
                self.admin_site.admin_view(ExportView.as_view(
                    serializer_class=self.serializer_class,
                    export_template_name=self.export_template_name,
                    modelAdmin=self)),
                name='%s_%s_export' % info),
        )
        return new_urls + urls

class ImportExportModelAdminMixin(ImportModelAdminMixin, ExportModelAdminMixin):
    pass

