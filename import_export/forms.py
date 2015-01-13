from __future__ import unicode_literals

import os.path

from .exceptions import ImportExportError
from .widgets import ForeignKeyWidget

from django import forms
from django.contrib.admin.helpers import ActionForm
from django.utils.translation import ugettext_lazy as _


class ValueOverrideMixin(object):
    def initialize_override_fields(self, resource):
        for name in resource.get_value_overrides():
            if name in resource.fields:
                field = resource.fields[name]
                if isinstance(field.widget, ForeignKeyWidget):
                    # Display a list of choices for foreign keys
                    formfield = forms.ChoiceField(required=False)
                    objects = field.widget.model.objects.all()
                    formfield.choices = [("", "---")] + [(obj.pk, str(obj)) for obj in objects]
                else:
                    formfield = forms.CharField(required=False)
            else:
                choices = ", ".join(resource.fields.keys())
                raise ImportExportError("Field %r does not exist (choices: %s)" % (name, choices))
            self.fields["override_{name}".format(name=name)] = formfield


class ImportForm(forms.Form, ValueOverrideMixin):
    import_file = forms.FileField(
            label=_('File to import')
            )
    input_format = forms.ChoiceField(
            label=_('Format'),
            choices=(),
            )

    def __init__(self, import_formats, resource, *args, **kwargs):
        super(ImportForm, self).__init__(*args, **kwargs)
        choices = []
        for i, f in enumerate(import_formats):
            choices.append((str(i), f().get_title(),))
        if len(import_formats) > 1:
            choices.insert(0, ('', '---'))

        self.fields['input_format'].choices = choices
        self.initialize_override_fields(resource)


class ConfirmImportForm(forms.Form, ValueOverrideMixin):
    import_file_name = forms.CharField(widget=forms.HiddenInput())
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
        super(ExportForm, self).__init__(*args, **kwargs)
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
