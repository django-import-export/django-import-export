import uuid
from pydoc import locate

from django.core.files.base import ContentFile
from django.core.mail.message import EmailMessage
from django.contrib.auth import get_user_model

from celery.app import shared_task

from .formats import base_formats


@shared_task
def export_data(file_format_name, queryset, resource_import_path, resource_kwargs, user_id, email_subject, *args, **kwargs):
    """
    Returns file_format representation for given queryset.
    """
    file_format_class = getattr(base_formats, file_format_name)
    file_format = file_format_class()

    User = get_user_model()
    user = User.objects.get(pk=user_id)

    resource_module_parts = resource_import_path.split('.')
    resource_name = resource_module_parts.pop()
    resource_module_name = '.'.join(resource_module_parts)
    resource_module = locate(resource_module_name)
    resource_class = getattr(resource_module, resource_name)
    resource = resource_class(**resource_kwargs)

    queryset = resource.get_queryset().filter(pk__in=queryset)

    data = resource.export(queryset, *args, **kwargs)
    exported_data = file_format.export_data(data)

    file_name = '{0}.{1}'.format(uuid.uuid4(), file_format.get_extension())

    export = ContentFile(exported_data, name=file_name)

    email_field = user.get_email_field_name()

    message = EmailMessage(email_subject, '', to=[getattr(user, email_field)])

    message.attach(file_name, export.read(), file_format.get_content_type())
    message.send()
