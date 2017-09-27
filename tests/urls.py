from __future__ import unicode_literals

from django.conf import settings
from django.conf.urls import url, include
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.contrib.staticfiles.views import serve


from django.contrib import admin
admin.autodiscover()


urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
]

urlpatterns += staticfiles_urlpatterns() + [
    url(r'^exported_files/(?P<path>.*)$', serve, {
            'document_root': settings.IMPORT_EXPORT_STORAGE_PATH,
        }),
]
