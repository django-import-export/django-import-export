from core import views

from django.conf.urls import url
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

admin.autodiscover()



urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^export/category/', views.CategoryExportView.as_view(),
        name='export-category'),
]

urlpatterns += staticfiles_urlpatterns()
