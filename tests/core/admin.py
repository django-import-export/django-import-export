from __future__ import unicode_literals

from django.contrib import admin

from import_export.admin import ImportExportMixin, ExportActionModelAdmin, RelatedModelImporterMixin, RelatedModelImportableAdmin

from .models import Book, Category, Author


class BookAdmin(ImportExportMixin, admin.ModelAdmin):
    list_filter = ['categories', 'author']


class BookImportable(RelatedModelImportableAdmin):
    origin_model = Author
    model = Book


class AuthorAdmin(RelatedModelImporterMixin, admin.ModelAdmin):
    related_importables = [BookImportable]


class CategoryAdmin(ExportActionModelAdmin):
    pass


admin.site.register(Book, BookAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(Author, AuthorAdmin)
