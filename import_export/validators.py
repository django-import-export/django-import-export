from django.core.exceptions import ValidationError


class ExportItemsValidator:
    def __init__(self, admin_instance, request):
        self.admin_instance = admin_instance
        self.request = request

    def __call__(self, value):
        export_ids = {str(i).strip() for i in value.strip("[]").split(",")}
        valid_ids = {
            str(pk)
            for pk in self.admin_instance.get_valid_export_item_pks(self.request)
        }
        invalid_ids = export_ids - valid_ids
        if invalid_ids:
            raise ValidationError(
                "Select a valid choice. "
                f"{','.join(invalid_ids)} is not one of the available choices."
            )
