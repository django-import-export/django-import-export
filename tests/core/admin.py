from django.contrib import admin

from import_export.admin import ImportExportMixin

from .models import Book


class BookAdmin(ImportExportMixin, admin.ModelAdmin):
    pass


admin.site.register(Book, BookAdmin)
