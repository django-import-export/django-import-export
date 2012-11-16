from django.conf.urls.defaults import patterns, include
from django.contrib.staticfiles.urls import staticfiles_urlpatterns


from django.contrib import admin
admin.autodiscover()


urlpatterns = patterns('',
        (r'^admin/', include(admin.site.urls)),
)

urlpatterns += staticfiles_urlpatterns()
