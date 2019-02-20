from django import forms

from import_export.forms import ConfirmImportForm, ImportForm

from .models import Author


class AuthorFormMixin(forms.Form):
    author = forms.ModelChoiceField(queryset=Author.objects.all(),
                                    required=True)


class CustomImportForm(AuthorFormMixin, ImportForm):
    """Customized ImportForm, with author field required"""
    pass


class CustomConfirmImportForm(AuthorFormMixin, ConfirmImportForm):
    """Customized ConfirmImportForm, with author field required"""
    pass
