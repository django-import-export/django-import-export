from django.contrib import admin

from import_export.admin import ImportMixin

from .models import Book


class BookAdmin(ImportMixin, admin.ModelAdmin):
    pass


admin.site.register(Book, BookAdmin)
