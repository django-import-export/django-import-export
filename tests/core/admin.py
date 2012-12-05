from django.contrib import admin

from import_export.admin import ImportExportMixin

from .models import Book, Category, Author


class BookAdmin(ImportExportMixin, admin.ModelAdmin):
    pass


admin.site.register(Book, BookAdmin)
admin.site.register(Category)
admin.site.register(Author)
