import os.path

from django import forms
from django.conf import settings
from django.contrib.admin.helpers import ActionForm
from django.utils.translation import gettext_lazy as _


class ImportForm(forms.Form):
    import_file = forms.FileField(
        label=_('File to import')
    )
    input_format = forms.ChoiceField(
        label=_('Format'),
        choices=(),
    )

    def __init__(self, import_formats, *args, **kwargs):
        super().__init__(*args, **kwargs)
        choices = [
            (str(i), f().get_title())
            for i, f in enumerate(import_formats)
        ]
        if len(import_formats) > 1:
            choices.insert(0, ('', '---'))
            self.fields['import_file'].widget.attrs['class'] = 'guess_format'
            self.fields['input_format'].widget.attrs['class'] = 'guess_format'

        self.fields['input_format'].choices = choices

    @property
    def media(self):
        extra = "" if settings.DEBUG else ".min"
        return forms.Media(
            js=(
                f'admin/js/vendor/jquery/jquery{extra}.js',
                'admin/js/jquery.init.js',
                'import_export/guess_format.js',
            )
        )


class ConfirmImportForm(forms.Form):
    import_file_name = forms.CharField(widget=forms.HiddenInput())
    original_file_name = forms.CharField(widget=forms.HiddenInput())
    input_format = forms.CharField(widget=forms.HiddenInput())

    def clean_import_file_name(self):
        data = self.cleaned_data['import_file_name']
        data = os.path.basename(data)
        return data


class ExportForm(forms.Form):
    file_format = forms.ChoiceField(
        label=_('Format'),
        choices=(),
        )

    def __init__(self, formats, *args, **kwargs):
        super().__init__(*args, **kwargs)
        choices = []
        for i, f in enumerate(formats):
            choices.append((str(i), f().get_title(),))
        if len(formats) > 1:
            choices.insert(0, ('', '---'))

        self.fields['file_format'].choices = choices


def export_action_form_factory(formats):
    """
    Returns an ActionForm subclass containing a ChoiceField populated with
    the given formats.
    """
    class _ExportActionForm(ActionForm):
        """
        Action form with export format ChoiceField.
        """
        file_format = forms.ChoiceField(
            label=_('Format'), choices=formats, required=False)
    _ExportActionForm.__name__ = str('ExportActionForm')

    return _ExportActionForm
