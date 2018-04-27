import os
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http.response import Http404, HttpResponse
from django.utils.decorators import method_decorator
from django.views.generic.base import View

from .formats import base_formats


class RetrieveExportedFileView(View):
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return View.dispatch(self, request, *args, **kwargs)

    def check_path(self, path):
        path_parts = path.split('.')
        format_class_name = path_parts[-1].upper()
        return len(path_parts) == 2 and hasattr(base_formats, format_class_name)

    def get(self, request, *args, **kwargs):
        path = kwargs.pop('path')
        if not self.check_path(path):
            raise Http404

        format_class_name = path.split('.')[-1]
        format_class_name = format_class_name.upper()
        file_format = getattr(base_formats, format_class_name)()
        content_type = file_format.get_content_type()

        full_file_path = os.path.join(settings.IMPORT_EXPORT_STORAGE_PATH, path)

        with open(full_file_path, 'r') as the_file:
            data = the_file.read()

        try:
            response = HttpResponse(data, content_type=content_type)
        except TypeError:
            response = HttpResponse(data, mimetype=content_type)

        response['Content-Disposition'] = 'attachment; filename=%s' % path

        return response
