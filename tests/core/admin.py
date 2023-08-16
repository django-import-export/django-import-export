from django.contrib import admin

from import_export.admin import (
    ExportActionModelAdmin,
    ImportExportMixin,
    ImportExportModelAdmin,
    ImportMixin,
)
from import_export.resources import ModelResource

from .forms import CustomConfirmImportForm, CustomExportForm, CustomImportForm
from .models import Author, Book, Category, Child, EBook, LegacyBook


class ChildAdmin(ImportMixin, admin.ModelAdmin):
    pass


class BookResource(ModelResource):
    class Meta:
        model = Book

    def for_delete(self, row, instance):
        return self.fields["name"].clean(row) == ""


class BookNameResource(ModelResource):
    class Meta:
        model = Book
        fields = ["id", "name"]
        name = "Export/Import only book names"


class BookAdmin(ImportExportModelAdmin):
    list_display = ("name", "author", "added")
    list_filter = ["categories", "author"]
    resource_classes = [BookResource, BookNameResource]
    change_list_template = "core/admin/change_list.html"


class ApplicationAdminMixin:
    # This simulates another application which overrides change_list change_list
    # This configuration is taken from django-admin-sortable2
    @property
    def change_list_template(self):
        return "core/admin/change_list.html"


class ApplicationModelAdmin(ImportExportMixin, ApplicationAdminMixin, admin.ModelAdmin):
    pass


class CategoryAdmin(ExportActionModelAdmin):
    pass


class AuthorAdmin(ImportMixin, admin.ModelAdmin):
    pass


class EBookResource(ModelResource):
    def __init__(self, **kwargs):
        super().__init__()
        self.author_id = kwargs.get("author_id")

    def filter_export(self, queryset, *args, **kwargs):
        return queryset.filter(author_id=self.author_id)

    class Meta:
        model = EBook


class CustomBookAdmin(ImportExportModelAdmin):
    """Example usage of custom import / export forms"""

    resource_classes = [EBookResource]
    import_form_class = CustomImportForm
    confirm_form_class = CustomConfirmImportForm
    export_form_class = CustomExportForm

    def get_confirm_form_initial(self, request, import_form):
        initial = super().get_confirm_form_initial(request, import_form)
        # Pass on the `author` value from the import form to
        # the confirm form (if provided)
        if import_form:
            initial["author"] = import_form.cleaned_data["author"].id
        return initial

    def get_import_resource_kwargs(self, request, *args, **kwargs):
        # update resource kwargs so that the Resource is passed the authenticated user
        # This is included as an example of how dynamic values
        # can be passed to resources
        kwargs = super().get_resource_kwargs(request, *args, **kwargs)
        kwargs.update({"user": request.user})
        return kwargs

    def get_export_resource_kwargs(self, request, *args, **kwargs):
        # this is overridden to demonstrate that custom form fields can be used
        # to override the export query.
        # The dict returned here will be passed as kwargs to EBookResource
        export_form = kwargs["export_form"]
        if export_form:
            return dict(author_id=export_form.cleaned_data["author"].id)
        return {}


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
