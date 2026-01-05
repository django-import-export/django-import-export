from django.core.exceptions import ValidationError


class ExportItemsValidator:
    def __init__(self, admin_instance, request):
        self.admin_instance = admin_instance
        self.request = request

    def __call__(self, value):
        export_ids = {str(i).strip() for i in value.strip("[]").split(",")}
        queryset = self.admin_instance.get_export_queryset(self.request)
        valid_ids = {str(pk) for pk in queryset.values_list("pk", flat=True)}
        invalid_ids = export_ids - valid_ids
        if invalid_ids:
            raise ValidationError(
                "Select a valid choice. "
                f"{','.join(invalid_ids)} is not one of the available choices."
            )
