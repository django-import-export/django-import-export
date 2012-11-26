from django import forms
from django.utils.translation import ugettext_lazy as _


class ImportForm(forms.Form):
    import_file = forms.FileField(
            label=_('File to import')
            )
    input_format = forms.ChoiceField(
            label=_('Format'),
            choices=(),
            )

    def __init__(self, format_choices, *args, **kwargs):
        super(ImportForm, self).__init__(*args, **kwargs)
        self.fields['input_format'].choices = format_choices


class ConfirmImportForm(forms.Form):
    import_file_name = forms.CharField(widget=forms.HiddenInput())
    input_format = forms.CharField(widget=forms.HiddenInput())
