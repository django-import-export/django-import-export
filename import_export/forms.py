from __future__ import unicode_literals

from django import forms
from django.utils.translation import ugettext_lazy as _


class ImportForm(forms.Form):
    import_file = forms.FileField(
            label=_('File to import')
            )


class ConfirmImportForm(forms.Form):
    import_file_name = forms.CharField(widget=forms.HiddenInput())
    import_file_mimetype = forms.CharField(widget=forms.HiddenInput())


class ExportForm(forms.Form):
    file_format = forms.ChoiceField(
            label=_('Format'),
            choices=(),
            )

    def __init__(self, formats, *args, **kwargs):
        super(ExportForm, self).__init__(*args, **kwargs)
        choices = []
        for i, f in enumerate(formats):
            choices.append((str(i), f().get_title(),))
        if len(formats) > 1:
            choices.insert(0, ('', '---'))

        self.fields['file_format'].choices = choices
