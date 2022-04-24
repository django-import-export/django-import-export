from django.contrib import admin

from import_export.admin import ExportActionModelAdmin, ImportExportMixin, ImportMixin
from import_export.resources import ModelResource

from .forms import CustomConfirmImportForm, CustomExportForm, CustomImportForm
from .models import Author, Book, Category, Child, EBook


class ChildAdmin(ImportMixin, admin.ModelAdmin):
    pass


class BookResource(ModelResource):

    class Meta:
        model = Book

    def for_delete(self, row, instance):
        return self.fields['name'].clean(row) == ''


class BookNameResource(ModelResource):

    class Meta:
        model = Book
        fields = ['id', 'name']
        name = "Export/Import only book names"


class BookAdmin(ImportExportMixin, admin.ModelAdmin):
    list_display = ('name', 'author', 'added')
    list_filter = ['categories', 'author']
    resource_classes = [BookResource, BookNameResource]


class CategoryAdmin(ExportActionModelAdmin):
    pass


class AuthorAdmin(ImportMixin, admin.ModelAdmin):
    pass


class CustomBookAdmin(BookAdmin):
    """BookAdmin with custom import forms"""

    def get_import_form_class(self, request):
        return CustomImportForm

    def get_confirm_form_class(self, request):
        return CustomConfirmImportForm

    def get_export_form_class(self):
        return CustomExportForm

    def get_confirm_form_initial(self, request, import_form):
        init_kwargs = dict()
        if import_form:
            init_kwargs = super().get_confirm_form_initial(request, import_form)
            author = import_form.cleaned_data['author']
            init_kwargs.update({'author': author.id})
        return init_kwargs


admin.site.register(Book, BookAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(Author, AuthorAdmin)
admin.site.register(Child, ChildAdmin)
admin.site.register(EBook, CustomBookAdmin)
