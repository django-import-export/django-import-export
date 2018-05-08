import importlib
import os
import pickle
import six
import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core.mail.message import EmailMessage
from django.db.models.sql import Query
from django.utils.translation import ugettext as _

from celery.app import shared_task
from celery.app.task import Task

from .formats import base_formats

USER_EMAIL_FIELD_NAME = getattr(settings, 'IMPORT_EXPORT_USER_EMAIL_FIELD_NAME', 'email')


class ExportData(Task):
    name = 'Export Data'

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        if not getattr(self, 'user', None):
            return super(ExportData, self).on_failure(exc, task_id, args, kwargs, einfo)

        email_address = self.get_email_address()

        if getattr(self, 'resource', None):
            model_name = self.resource._meta.model.__name__
            message_content = _("Your attempt to export %ss failed.") % model_name.lower()
        else:
            model_name = ''
            message_content = ''

        subject = (_("%s Export failed") % model_name).strip()

        message = EmailMessage(subject, message_content, to=[email_address])

        message.send()

    def get_resource(self, resource_import_path, resource_kwargs):
        resource_module_parts = resource_import_path.split('.')
        resource_name = resource_module_parts.pop()
        resource_module_name = '.'.join(resource_module_parts)
        resource_module = importlib.import_module(resource_module_name)
        resource_class = getattr(resource_module, resource_name)
        return resource_class(**resource_kwargs)

    def get_file_name(self):
        file_name = '%s.%s' % (uuid.uuid4().hex, self.file_format.get_extension())
        return file_name

    def deserialize_query(self, pickled_query):
        query = pickle.loads(pickled_query)
        # query could be anything. It should be an instance of the Query class and
        # if it isn't then something is very wrong
        assert isinstance(query, Query)
        return query

    def get_user(self, user_id):
        User = get_user_model()
        return User.objects.get(pk=user_id)

    def export_data(self, *args, **kwargs):
        data = self.resource.export(self.queryset, *args, **kwargs)
        exported_data = self.file_format.export_data(data)

        if isinstance(exported_data, six.text_type):
            exported_data = exported_data.encode('utf-8')

        if not os.path.isdir(settings.IMPORT_EXPORT_STORAGE_PATH):
            os.mkdir(settings.IMPORT_EXPORT_STORAGE_PATH)

        with open(os.path.join(settings.IMPORT_EXPORT_STORAGE_PATH, self.file_name), 'wb') as the_file:
            the_file.write(exported_data)

    def get_email_address(self):
        email_field = self.user.get_email_field_name() if hasattr(self.user, 'get_email_field_name') else USER_EMAIL_FIELD_NAME
        return getattr(self.user, email_field)

    def send_email(self, subject):
        email_address = self.get_email_address()

        message_content = _("Your exported data can be downloaded from http://%s/%s/%s") % (
            Site.objects.get_current().domain,
            settings.IMPORT_EXPORT_STORAGE_URL,
            self.file_name
        )

        message = EmailMessage(subject, message_content, to=[email_address])

        message.send()


@shared_task(bind=True, base=ExportData)
def export_data(self, file_format_name, pickled_query, resource_import_path, resource_kwargs, user_id, email_subject, *args, **kwargs):
    file_format_class = getattr(base_formats, file_format_name)
    self.user = self.get_user(user_id)
    self.file_format = file_format_class()
    self.resource = self.get_resource(resource_import_path, resource_kwargs)
    self.file_name = self.get_file_name()
    self.queryset = self.resource.get_queryset()
    self.queryset.query = self.deserialize_query(pickled_query)
    self.export_data()
    self.send_email(email_subject)
