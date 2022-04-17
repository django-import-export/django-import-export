from django.contrib import admin

from import_export import widgets, fields
from import_export.admin import ExportActionModelAdmin, ImportExportMixin, ImportMixin
from import_export.resources import ModelResource


from .forms import CustomConfirmImportForm, CustomImportForm
from .models import Author, Book, Category, Child, EBook


class ChildAdmin(ImportMixin, admin.ModelAdmin):
    pass


class CategoryResource(ModelResource):

    class Meta:
        model = Category

class AuthorResource(ModelResource):

    class Meta:
        model = Author

class BookResource(ModelResource):

    categories = fields.Field(
        attribute="categories",
        column_name="categories",
        widget=widgets.ResourceWidget(
            model=Category, resource_class=CategoryResource, is_m2m=True
        )
    )

    author = fields.Field(
        attribute="author",
        column_name="author",
        widget=widgets.ResourceWidget(
            model=Author, resource_class=AuthorResource
        )
    )

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

    def get_import_form(self):
        return CustomImportForm

    def get_confirm_import_form(self):
        return CustomConfirmImportForm

    def get_form_kwargs(self, form, *args, **kwargs):
        # update kwargs with authors (from CustomImportForm.cleaned_data)
        if isinstance(form, CustomImportForm):
            if form.is_valid():
                author = form.cleaned_data['author']
                kwargs.update({'author': author.id})
        return kwargs


admin.site.register(Book, BookAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(Author, AuthorAdmin)
admin.site.register(Child, ChildAdmin)
admin.site.register(EBook, CustomBookAdmin)
