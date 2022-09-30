from django.contrib import admin
from django.core.exceptions import ValidationError

from import_export.admin import ExportActionModelAdmin, ImportExportMixin, ImportMixin
from import_export.resources import ModelResource
from import_export.results import RowResult

from .forms import CustomConfirmImportForm, CustomExportForm, CustomImportForm
from .models import Author, Book, Category, Child, EBook, LegacyBook


class ChildAdmin(ImportMixin, admin.ModelAdmin):
    pass


class BookWithWarningsResource(ModelResource):
    class Meta:
        model = Book

    def import_row(
        self,
        row,
        instance_loader,
        using_transactions=True,
        dry_run=False,
        raise_errors=False,
        **kwargs
    ):
        row_result = super().import_row(
            row, instance_loader, using_transactions, dry_run, raise_errors, **kwargs
        )
        row_result.append_warning("Warning in row")
        if row.get("id") != '1':
            row_result = self.get_row_result_class()()
            row_result.import_type = RowResult.IMPORT_TYPE_INVALID
            row_result.validation_error = ValidationError("Invalid record")
            row_result.append_warning("Warning in validation")
        return row_result


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
    resource_classes = [BookResource, BookNameResource, BookWithWarningsResource]
    change_list_template = "core/admin/change_list.html"


class CategoryAdmin(ExportActionModelAdmin):
    pass


class AuthorAdmin(ImportMixin, admin.ModelAdmin):
    pass


class CustomBookAdmin(BookAdmin):
    """BookAdmin with custom import forms"""

    import_form_class = CustomImportForm
    confirm_form_class = CustomConfirmImportForm
    export_form_class = CustomExportForm

    def get_confirm_form_initial(self, request, import_form):
        initial = super().get_confirm_form_initial(request, import_form)
        # Pass on the `author` value from the import form to
        # the confirm form (if provided)
        if import_form:
            initial['author'] = import_form.cleaned_data['author'].id
        return initial


class LegacyBookAdmin(BookAdmin):
    """
    BookAdmin with deprecated function overrides.
    This class exists solely to test import works correctly using the deprecated
    functions.
    This class can be removed when the deprecated code is removed.
    """

    def get_import_form(self):
        return super().get_import_form()

    def get_confirm_import_form(self):
        return super().get_confirm_import_form()

    def get_form_kwargs(self, form, *args, **kwargs):
        return super().get_form_kwargs(form, *args, **kwargs)

    def get_export_form(self):
        return super().get_export_form()


admin.site.register(Book, BookAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(Author, AuthorAdmin)
admin.site.register(Child, ChildAdmin)
admin.site.register(EBook, CustomBookAdmin)
admin.site.register(LegacyBook, LegacyBookAdmin)
