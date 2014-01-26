from __future__ import unicode_literals

from django.conf.urls import patterns, include
from django.contrib.staticfiles.urls import staticfiles_urlpatterns


from django.contrib import admin
admin.autodiscover()


urlpatterns = patterns('',
        (r'^admin/', include(admin.site.urls)),
)

urlpatterns += staticfiles_urlpatterns()
