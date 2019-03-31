from __future__ import unicode_literals

import mimetypes
import argparse

from django.apps import apps as django_apps
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.encoding import force_text
from django.utils.translation import ugettext as _
from django.utils.module_loading import import_string

from import_export.formats import base_formats
from import_export.resources import modelresource_factory


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.formatter_class = argparse.ArgumentDefaultsHelpFormatter
        resource_def = parser.add_mutually_exclusive_group(required=True)

        parser.add_argument(
            'file-path',
            type=str,
            help='File path to import')
        resource_def.add_argument(
            '--resource',
            dest='resource',
            default=None,
            help='Resource class as dotted path,'
            'e.g.: mymodule.resources.MyResource')
        resource_def.add_argument(
            '--model',
            dest='model',
            default=None,
            help='Model class as dotted path, e.g.: myapp.models.MyModel')
        parser.add_argument(
            '--dry-run',
            action='store_true',
            dest='dry_run',
            default=False,
            help='Dry run')
        parser.add_argument(
            '--raise-errors',
            action='store_true',
            dest='raise_errors',
            help='Raise errors')
        parser.add_argument(
            '--no-raise-errors',
            action='store_false',
            dest='raise_errors',
            help='Do not raise errors')
        parser.add_argument(
            '--totals',
            action='store_true',
            dest='show_totals',
            default=False,
            help='Show total numbers of performed actions by type')

    @transaction.atomic
    def handle(self, **options):
        file_name, dry_run, raise_errors = self.extract_options(options)
        resource = self.get_resource(options)

        result = self.import_file(file_name, resource,
                                  dry_run=dry_run, raise_errors=raise_errors)

        if options.get('show_totals'):
            self.stdout.write(', '.join(
                ['{} {}'.format(v, k) for k, v in result.totals.items() if v]
            ))

        if result.has_errors():
            self.stdout.write(self.style.ERROR(_('Errors')))
            for error in result.base_errors:
                self.stdout.write(str(error.error), self.style.ERROR)
            for line, errors in result.row_errors():
                for error in errors:
                    self.stdout.write(self.style.ERROR(
                        _('Line number') + ': ' + force_text(line) + ' - '
                        + force_text(error.error)))
        else:
            self.stdout.write(self.style.HTTP_REDIRECT(_('OK')))

    def import_file(self, file_name, resource, dry_run, raise_errors):
        mimetype = mimetypes.guess_type(file_name)[0]
        input_format = (base_formats.get_format_for_content_type(mimetype)
                        or base_formats.CSV)()
        read_mode = input_format.get_read_mode()
        try:
            with open(file_name, read_mode) as import_file:
                data = import_file.read()
        except (OSError, FileNotFoundError) as e:
            raise CommandError(str(e))
        dataset = input_format.create_dataset(data)
        result = resource.import_data(
            dataset,
            dry_run=dry_run,
            raise_errors=raise_errors
        )
        return result

    def extract_options(self, options):
        dry_run = options.get('dry_run')
        if dry_run:
            self.stdout.write(self.style.NOTICE(_('Dry run')))
        raise_errors = options.get('raise_errors', None)
        if raise_errors is None:
            raise_errors = not dry_run
        file_name = options.get('file-path')
        return file_name, dry_run, raise_errors

    def get_resource(self, options):
        if options.get('resource', False):
            resource_class = import_string(options['resource'])
        else:
            model = django_apps.get_model(options.get('model'))
            resource_class = modelresource_factory(model)
        resource = resource_class()
        return resource
