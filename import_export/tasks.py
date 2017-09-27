import uuid
import importlib
import os
import pickle

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core.files.base import ContentFile, File
from django.core.mail.message import EmailMessage
from django.db.models.sql import Query
from django.utils.translation import ugettext as _

from celery.app import shared_task

from .formats import base_formats


def _get_resource(resource_import_path, resource_kwargs):
    resource_module_parts = resource_import_path.split('.')
    resource_name = resource_module_parts.pop()
    resource_module_name = '.'.join(resource_module_parts)
    resource_module = importlib.import_module(resource_module_name)
    resource_class = getattr(resource_module, resource_name)
    return resource_class(**resource_kwargs)


def _get_exported_data_as_attachment(file_format, resource, pickled_query, *args, **kwargs):
    query = pickle.loads(pickled_query)
    # query could be anything. It should be an instance of the Query class and
    # if it isn't then something is very wrong
    assert isinstance(query, Query)
    queryset = resource.get_queryset()
    queryset.query = query

    data = resource.export(queryset, *args, **kwargs)
    exported_data = file_format.export_data(data)

    file_name = '%s.%s' % (uuid.uuid4().hex, file_format.get_extension())

    return ContentFile(exported_data, name=file_name)


def _get_email_message(subject, user, data):
    email_field = user.get_email_field_name()

    if not os.path.isdir(settings.IMPORT_EXPORT_STORAGE_PATH):
        os.mkdir(settings.IMPORT_EXPORT_STORAGE_PATH)

    with open(os.path.join(settings.IMPORT_EXPORT_STORAGE_PATH, data.name), 'w') as the_file:
        the_file.write(data.read())

    message_content = _("Your exported data can be downloaded from http://%s/%s/%s") % (Site.objects.get_current().domain, settings.IMPORT_EXPORT_STORAGE_URL, data.name)

    message = EmailMessage(subject, message_content, to=[getattr(user, email_field)])

    return message


@shared_task
def export_data(file_format_name, pickled_query, resource_import_path, resource_kwargs, user_id, email_subject, *args, **kwargs):
    """
    Returns file_format representation for given queryset.
    """
    file_format_class = getattr(base_formats, file_format_name)
    file_format = file_format_class()

    resource = _get_resource(resource_import_path, resource_kwargs)

    export = _get_exported_data_as_attachment(file_format, resource, pickled_query, *args, **kwargs)

    User = get_user_model()
    user = User.objects.get(pk=user_id)

    message = _get_email_message(email_subject, user, export)

    message.send()
