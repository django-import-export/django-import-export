from __future__ import unicode_literals

import mimetypes
import argparse

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.encoding import force_text
from django.utils.translation import ugettext as _

from import_export.formats import base_formats

from django.apps import apps as django_apps


FORMATS = {
    None: base_formats.CSV,
    'text/csv': base_formats.CSV,
    'application/json': base_formats.JSON,
    'text/yaml': base_formats.YAML,
    'text/tab-separated-values': base_formats.TSV,
    'application/vnd.oasis.opendocument.spreadsheet': base_formats.ODS,
    'text/html': base_formats.HTML,
    'application/vnd.ms-excel': base_formats.XLS,
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':
        base_formats.XLSX,
}


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.formatter_class = argparse.ArgumentDefaultsHelpFormatter

        parser.add_argument(
            'file-path',
            metavar='file-path',
            nargs=1,
            help='File path to import')
        parser.add_argument(
            '--resource-class',
            dest='resource_class',
            default=None,
            help='Resource class as dotted path,'
            'ie: mymodule.resources.MyResource')
        parser.add_argument(
            '--model-name',
            dest='model_name',
            default=None,
            help='Model name, ie: auth.User')
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

    def get_resource_class(self, resource_class, model_name):
        from django.utils.module_loading import import_string
        from import_export.resources import modelresource_factory

        if not resource_class:
            return modelresource_factory(django_apps.get_model(model_name))
        else:
            return import_string(resource_class)

    @transaction.atomic
    def handle(self, **options):
        dry_run = options.get('dry_run')
        if dry_run:
            self.stdout.write(self.style.NOTICE(_('Dry run')))
        raise_errors = options.get('raise_errors', None)
        if raise_errors is None:
            raise_errors = not dry_run
        import_file_name = options['file-path'][0]
        mimetype = mimetypes.guess_type(import_file_name)[0]
        input_format = FORMATS[mimetype]()
        resource_class = self.get_resource_class(
            options.get('resource_class'),
            options.get('model_name')
        )
        resource = resource_class()
        read_mode = input_format.get_read_mode()
        try:
            with open(import_file_name, read_mode) as import_file:
                data = import_file.read()
        except (OSError, FileNotFoundError) as e:
            raise CommandError(str(e))
        dataset = input_format.create_dataset(data)
        result = resource.import_data(
            dataset,
            dry_run=dry_run,
            raise_errors=raise_errors
        )

        if options.get('show_totals'):
            self.stdout.write(', '.join(
                ['{} {}'.format(v, k) for k, v in result.totals.items()]
            ))

        if result.has_errors():
            self.stdout.write(self.style.ERROR(_('Errors')))
            for error in result.base_errors:
                self.stdout.write(error.error, self.style.ERROR)
            for line, errors in result.row_errors():
                for error in errors:
                    self.stdout.write(self.style.ERROR(
                        _('Line number') + ': ' + force_text(line) + ' - '
                        + force_text(error.error)))
        else:
            self.stdout.write(self.style.HTTP_REDIRECT(_('OK')))
