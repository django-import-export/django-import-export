from django.contrib import admin

from import_export.admin import ExportActionModelAdmin, ImportExportMixin, ImportMixin
from import_export.resources import ModelResource

from .models import Author, Book, Category, Child


class ChildAdmin(ImportMixin, admin.ModelAdmin):
    pass


class BookResource(ModelResource):

    class Meta:
        model = Book

    def for_delete(self, row, instance):
        return self.fields['name'].clean(row) == ''


class BookAdmin(ImportExportMixin, admin.ModelAdmin):
    list_filter = ['categories', 'author']
    resource_class = BookResource


class CategoryAdmin(ExportActionModelAdmin):
    pass


class AuthorAdmin(ImportMixin, admin.ModelAdmin):
    pass

admin.site.register(Book, BookAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(Author, AuthorAdmin)
admin.site.register(Child, ChildAdmin)
