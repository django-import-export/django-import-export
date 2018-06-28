from __future__ import unicode_literals

from django.conf.urls import url, include
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from django.contrib import admin
admin.autodiscover()

from core import views


urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^export/category/', views.CategoryExportView.as_view(),
        name='export-category'),
]

urlpatterns += staticfiles_urlpatterns()
