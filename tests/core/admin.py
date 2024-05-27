from django.contrib import admin

from import_export.admin import (
    ExportActionModelAdmin,
    ImportExportModelAdmin,
    ImportMixin,
)
from import_export.fields import Field
from import_export.resources import ModelResource

from .forms import CustomConfirmImportForm, CustomExportForm, CustomImportForm
from .models import Author, Book, Category, Child, EBook, UUIDBook, UUIDCategory


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


class CategoryAdmin(ExportActionModelAdmin):
    pass


class UUIDBookAdmin(ImportExportModelAdmin):
    pass


class UUIDCategoryAdmin(ExportActionModelAdmin):
    pass


class AuthorAdmin(ImportMixin, admin.ModelAdmin):
    pass


class UUIDBookResource(ModelResource):
    class Meta:
        model = UUIDBook


class EBookResource(ModelResource):
    published = Field(attribute="published", column_name="published_date")
    author_email = Field(attribute="author_email", column_name="Email of the author")

    def __init__(self, **kwargs):
        super().__init__()
        self.author_id = kwargs.get("author_id")

    def filter_export(self, queryset, **kwargs):
        return queryset.filter(author_id=self.author_id)

    class Meta:
        model = EBook
        fields = ("id", "author_email", "name", "published")


class CustomBookAdmin(ExportActionModelAdmin, ImportExportModelAdmin):
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

    def get_import_resource_kwargs(self, request, **kwargs):
        # update resource kwargs so that the Resource is passed the authenticated user
        # This is included as an example of how dynamic values
        # can be passed to resources
        if "form" not in kwargs:
            # test for #1789
            raise ValueError("'form' param was expected in kwargs")
        kwargs = super().get_resource_kwargs(request, **kwargs)
        kwargs.update({"user": request.user})
        return kwargs

    def get_export_resource_kwargs(self, request, **kwargs):
        # this is overridden to demonstrate that custom form fields can be used
        # to override the export query.
        # The dict returned here will be passed as kwargs to EBookResource
        export_form = kwargs.get("export_form")
        if export_form:
            kwargs.update(author_id=export_form.cleaned_data["author"].id)
        return kwargs


admin.site.register(Book, BookAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(Author, AuthorAdmin)
admin.site.register(Child, ChildAdmin)
admin.site.register(EBook, CustomBookAdmin)
admin.site.register(UUIDCategory, UUIDCategoryAdmin)
admin.site.register(UUIDBook, UUIDBookAdmin)
