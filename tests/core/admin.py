from django.contrib import admin

from import_export.admin import ImportExportMixin

from .models import Book, Category, Author


class BookAdmin(ImportExportMixin, admin.ModelAdmin):
    list_filter = ['categories', 'author']

    def has_add_permission(self, request):
        return False


admin.site.register(Book, BookAdmin)
admin.site.register(Category)
admin.site.register(Author)
