from __future__ import unicode_literals

from django.conf.urls import url, include
from django.contrib.staticfiles.urls import staticfiles_urlpatterns


from django.contrib import admin
admin.autodiscover()

from import_export.views import RetrieveExportedFileView


urlpatterns = [
    url(r'^admin/', admin.site.urls),
]

urlpatterns += staticfiles_urlpatterns() + [
    url(r'^exported_files/(?P<path>.*)$', RetrieveExportedFileView.as_view()),
]
