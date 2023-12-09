from django import forms
from django.core.exceptions import ValidationError

from import_export.forms import ConfirmImportForm, ExportForm, ImportForm

from .models import Author, Book


class ModelFieldMixin(forms.Form):
    model_fields = forms.MultipleChoiceField(label="Export Fields", required=True)
    model = Book

    # For exporting data, you must select at least one of the required fields.
    # Please ensure that your selection includes at least one of these fields
    required_model_fields = ["id", "name", "author", "author_email"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["model_fields"].choices = [
            (field.name, field.name) for field in self.model._meta.get_fields()
        ]

    def clean_model_fields(self):
        minimum_field_selection = 2
        data = self.cleaned_data["model_fields"]
        missing_required_fields = not any(
            item in data for item in self.required_model_fields
        )
        if len(data) < minimum_field_selection:
            raise ValidationError("Minimum field selection is two field.")
        if missing_required_fields:
            raise ValidationError(
                f"Required fields are missing. Please select at least one of these fields: {', '.join(self.required_model_fields)}"
            )

        return data


class AuthorFormMixin(forms.Form):
    author = forms.ModelChoiceField(queryset=Author.objects.all(), required=True)


class CustomImportForm(AuthorFormMixin, ImportForm):
    """Customized ImportForm, with author field required"""

    pass


class CustomConfirmImportForm(AuthorFormMixin, ConfirmImportForm):
    """Customized ConfirmImportForm, with author field required"""

    pass


class CustomExportForm(AuthorFormMixin, ExportForm):
    """Customized ExportForm, with author field required"""

    pass


class CustomExportFormModelFields(ExportForm, ModelFieldMixin):
    """Customized ExportForm, with model fields"""

    pass
