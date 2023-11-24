import os.path

from django import forms
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class ImportExportFormBase(forms.Form):
    resource = forms.ChoiceField(
        label=_("Resource"),
        choices=(),
        required=False,
    )
    format = forms.ChoiceField(
        label=_("Format"),
        choices=(),
    )

    def __init__(self, *args, formats=None, resources=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._init_resources(resources)
        self._init_formats(formats)

    def _init_resources(self, resources):
        if not resources:
            raise ValueError("no defined resources")
        if len(resources) == 1:
            self.fields["resource"].value = resources[0].get_display_name()
            self.fields["resource"].widget.attrs["readonly"] = True
        if len(resources) > 1:
            resource_choices = []
            for i, resource in enumerate(resources):
                resource_choices.append((i, resource.get_display_name()))
            self.fields["resource"].choices = resource_choices

    def _init_formats(self, formats):
        if not formats:
            raise ValueError("invalid formats list")

        choices = [(str(i), f().get_title()) for i, f in enumerate(formats)]
        if len(formats) == 1:
            field = self.fields["format"]
            field.value = formats[0]().get_title()
            field.initial = 0
            field.widget.attrs["readonly"] = True
        if len(formats) > 1:
            choices.insert(0, ("", "---"))

        self.fields["format"].choices = choices


class ImportForm(ImportExportFormBase):
    import_file = forms.FileField(label=_("File to import"))

    # field ordered for usability:
    # ensure that the 'file' select appears before 'format'
    # so that the 'guess_format' js logic makes sense
    field_order = ["resource", "import_file", "format"]

    def __init__(self, *args, formats=None, resources=None, **kwargs):
        super().__init__(*args, formats=formats, resources=resources, **kwargs)
        if len(formats) > 1:
            self.fields["import_file"].widget.attrs["class"] = "guess_format"
            self.fields["format"].widget.attrs["class"] = "guess_format"

    @property
    def media(self):
        extra = "" if settings.DEBUG else ".min"
        return forms.Media(
            js=(
                f"admin/js/vendor/jquery/jquery{extra}.js",
                "admin/js/jquery.init.js",
                "import_export/guess_format.js",
            )
        )


class ConfirmImportForm(forms.Form):
    import_file_name = forms.CharField(widget=forms.HiddenInput())
    original_file_name = forms.CharField(widget=forms.HiddenInput())
    format = forms.CharField(widget=forms.HiddenInput())
    resource = forms.CharField(widget=forms.HiddenInput(), required=False)

    def clean_import_file_name(self):
        data = self.cleaned_data["import_file_name"]
        data = os.path.basename(data)
        return data


class ExportForm(ImportExportFormBase):
    export_items = forms.MultipleChoiceField(
        widget=forms.MultipleHiddenInput(), required=False
    )
