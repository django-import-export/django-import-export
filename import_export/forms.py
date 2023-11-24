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

    def __init__(self, *args, resources=None, **kwargs):
        super().__init__(*args, **kwargs)
        if not resources:
            raise ValueError("no defined resources")
        if len(resources) > 1:
            resource_choices = []
            for i, resource in enumerate(resources):
                resource_choices.append((i, resource.get_display_name()))
            self.fields["resource"].choices = resource_choices
        else:
            self.fields["resource"].value = resources[0].get_display_name()
            self.fields["resource"].widget.attrs["readonly"] = True


class ImportForm(ImportExportFormBase):
    import_file = forms.FileField(label=_("File to import"))
    input_format = forms.ChoiceField(
        label=_("Format"),
        choices=(),
    )

    def __init__(self, import_formats, *args, **kwargs):
        resources = kwargs.pop("resources", None)
        super().__init__(*args, resources=resources, **kwargs)
        choices = [(str(i), f().get_title()) for i, f in enumerate(import_formats)]
        if len(import_formats) > 1:
            choices.insert(0, ("", "---"))
            self.fields["import_file"].widget.attrs["class"] = "guess_format"
            self.fields["input_format"].widget.attrs["class"] = "guess_format"

        self.fields["input_format"].choices = choices

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
    input_format = forms.CharField(widget=forms.HiddenInput())
    resource = forms.CharField(widget=forms.HiddenInput(), required=False)

    def clean_import_file_name(self):
        data = self.cleaned_data["import_file_name"]
        data = os.path.basename(data)
        return data


class ExportForm(ImportExportFormBase):
    file_format = forms.ChoiceField(
        label=_("Format"),
        choices=(),
    )
    export_items = forms.MultipleChoiceField(
        widget=forms.MultipleHiddenInput(), required=False
    )

    def __init__(self, formats, *args, **kwargs):
        resources = kwargs.pop("resources", None)
        super().__init__(*args, resources=resources, **kwargs)
        choices = []
        for i, f in enumerate(formats):
            choices.append(
                (
                    str(i),
                    f().get_title(),
                )
            )
        if len(formats) > 1:
            choices.insert(0, ("", "---"))
        elif len(formats) == 1:
            field = self.fields["file_format"]
            field.value = formats[0]().get_title()
            field.initial = 0
            field.widget.attrs["readonly"] = True
        else:
            raise ValueError("invalid export formats list")

        self.fields["file_format"].choices = choices
