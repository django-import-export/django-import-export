==============================
Installation and configuration
==============================

import-export is available on the Python Package Index (PyPI), so it
can be installed with standard Python tools like ``pip`` or ``easy_install``::

  pip install django-import-export

This will automatically install the default formats supported by tablib.
If you need additional formats you should install the extra dependencies as required
appropriate tablib dependencies (e.g. ``pip install django-import-export[xlsx]``).

To install all available formats, use ``pip install django-import-export[all]``.

For all formats, see the
`tablib documentation <https://tablib.readthedocs.io/en/stable/formats.html>`_.

Alternatively, you can install the git repository directly to obtain the
development version::

  pip install -e git+https://github.com/django-import-export/django-import-export.git#egg=django-import-export

Now, you're good to go, unless you want to use import-export from the
admin as well. In this case, you need to add it to your ``INSTALLED_APPS`` and
let Django collect its static files.

.. code-block:: python

    # settings.py
    INSTALLED_APPS = (
        ...
        'import_export',
    )

.. code-block:: shell

    $ python manage.py collectstatic

All prerequisites are set up! See :doc:`getting_started` to learn how to use
import-export in your project.

Settings
========

You can configure the following in your settings file:

``IMPORT_EXPORT_USE_TRANSACTIONS``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Controls if resource importing should use database transactions. Defaults to
``True``. Using transactions makes imports safer as a failure during import
won’t import only part of the data set.

Can be overridden on a ``Resource`` class by setting the
``use_transactions`` class attribute.

``IMPORT_EXPORT_SKIP_ADMIN_LOG``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If set to ``True``, skips the creation of admin log entries when importing via the
:ref:`Admin UI<admin-integration>`.
Defaults to ``False``. This can speed up importing large data sets, at the cost
of losing an audit trail.

Can be overridden on a ``ModelAdmin`` class inheriting from ``ImportMixin`` by
setting the ``skip_admin_log`` class attribute.

.. _import_export_tmp_storage_class:

``IMPORT_EXPORT_TMP_STORAGE_CLASS``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A string path to the preferred temporary storage module.

Controls which storage class to use for storing the temporary uploaded file
during imports. Defaults to ``import_export.tmp_storages.TempFolderStorage``.

Can be overridden on a ``ModelAdmin`` class inheriting from ``ImportMixin`` by
setting the ``tmp_storage_class`` class attribute.

.. _import_export_default_file_storage:

``IMPORT_EXPORT_DEFAULT_FILE_STORAGE``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A string path to a customized storage implementation.

This setting is deprecated and only applies if using Django with a version less than 4.2,
and will be removed in a future release.

.. _import_export_import_permission_code:

``IMPORT_EXPORT_IMPORT_PERMISSION_CODE``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If set, lists the permission code that is required for users to perform the
'import' action. Defaults to ``None``, which means all users can perform
imports.

Django’s built-in permissions have the codes ``add``, ``change``, ``delete``,
and ``view``.  You can also add your own permissions.  For example, if you set this
value to 'import', then you can define an explicit permission for import in the example
app with:

.. code-block:: python

  from core.models import Book
  from django.contrib.auth.models import Permission
  from django.contrib.contenttypes.models import ContentType

  content_type = ContentType.objects.get_for_model(Book)
  permission = Permission.objects.create(
    codename="import_book",
    name="Can import book",
    content_type=content_type,
  )

Now only users who are assigned 'import_book' permission will be able to perform
imports.  For more information refer to the
`Django auth <https://docs.djangoproject.com/en/stable/topics/auth/default/>`_
documentation.

.. _import_export_export_permission_code:

``IMPORT_EXPORT_EXPORT_PERMISSION_CODE``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Defines the same behaviour as :ref:`IMPORT_EXPORT_IMPORT_PERMISSION_CODE`, but for
export.

``IMPORT_EXPORT_CHUNK_SIZE``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

An integer that defines the size of chunks when iterating a QuerySet for data
exports. Defaults to ``100``. You may be able to save memory usage by
decreasing it, or speed up exports by increasing it.

Can be overridden on a ``Resource`` class by setting the ``chunk_size`` class
attribute.

.. _import_export_skip_admin_confirm:

``IMPORT_EXPORT_SKIP_ADMIN_CONFIRM``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If ``True``, no import confirmation page will be presented to the user in the Admin UI.
The file will be imported in a single step.

By default, the import will occur in a transaction.
If the import causes any runtime errors (including validation errors),
then the errors are presented to the user and then entire transaction is rolled back.

Note that if you disable transaction support via configuration (or if your database
does not support transactions), then validation errors will still be presented to the user
but valid rows will have imported.

This flag can be enabled for the model admin using the :attr:`~import_export.mixins.BaseImportMixin.skip_import_confirm`
flag.

.. _import_export_skip_admin_export_ui:

``IMPORT_EXPORT_SKIP_ADMIN_EXPORT_UI``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A boolean value which will skip the :ref:`export form<admin_ui_exporting>` in the Admin UI, when the export is
initiated from the :ref:`change list page<admin_ui_exporting>`.
The file will be exported in a single step.

If enabled:

* the first element in the :attr:`~import_export.mixins.BaseImportExportMixin.resource_classes` list will be used.
* the first element in the :ref:`export_formats` list will be used.

This flag can be enabled for the model admin using the :attr:`~import_export.mixins.BaseExportMixin.skip_export_form`
flag.

.. _import_export_skip_admin_action_export_ui:

``IMPORT_EXPORT_SKIP_ADMIN_ACTION_EXPORT_UI``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A boolean value which will skip the :ref:`export form<admin_ui_exporting>` in the Admin UI, but only when the export is
requested from an :ref:`Admin UI action<export_via_admin_action>`, or from the 'Export' button on the
:ref:`change form <export_from_model_change_form>`.

.. _import_export_escape_formulae_on_export:

``IMPORT_EXPORT_ESCAPE_FORMULAE_ON_EXPORT``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If set to ``True``, strings will be sanitized by removing any leading '=' character.  This is to prevent execution of
Excel formulae.  By default this is ``False``.

.. _import_export_escape_illegal_chars_on_export:

``IMPORT_EXPORT_ESCAPE_ILLEGAL_CHARS_ON_EXPORT``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If an export to XLSX format generates
`IllegalCharacterError <https://openpyxl.readthedocs.io/en/latest/api/openpyxl.utils.exceptions.html>`_, then
if this flag is ``True`` strings will be sanitized by removing any invalid Excel characters,
replacing them with the unicode replacement character.
By default this is ``False``, meaning that ``IllegalCharacterError`` is caught and re-raised as ``ValueError``.

.. _import_export_formats:

``IMPORT_EXPORT_FORMATS``
~~~~~~~~~~~~~~~~~~~~~~~~~

A list that defines which file formats will be allowed during imports and exports. Defaults
to ``import_export.formats.base_formats.DEFAULT_FORMATS``.
The values must be those provided in ``import_export.formats.base_formats`` e.g

.. code-block:: python

    # settings.py
    from import_export.formats.base_formats import XLSX
    IMPORT_EXPORT_FORMATS = [XLSX]

This can be set for a specific model admin by declaring the ``formats`` attribute.

.. _import_formats:

``IMPORT_FORMATS``
~~~~~~~~~~~~~~~~~~

A list that defines which file formats will be allowed during imports. Defaults
to ``IMPORT_EXPORT_FORMATS``.
The values must be those provided in ``import_export.formats.base_formats`` e.g

.. code-block:: python

    # settings.py
    from import_export.formats.base_formats import CSV, XLSX
    IMPORT_FORMATS = [CSV, XLSX]

This can be set for a specific model admin by declaring the ``import_formats`` attribute.

.. _export_formats:

``EXPORT_FORMATS``
~~~~~~~~~~~~~~~~~~

A list that defines which file formats will be allowed during exports. Defaults
to ``IMPORT_EXPORT_FORMATS``.
The values must be those provided in ``import_export.formats.base_formats`` e.g

.. code-block:: python

    # settings.py
    from import_export.formats.base_formats import XLSX
    EXPORT_FORMATS = [XLSX]

This can be set for a specific model admin by declaring the ``export_formats`` attribute.

.. _import_export_import_ignore_blank_lines:

``IMPORT_EXPORT_IMPORT_IGNORE_BLANK_LINES``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If set to ``True``, rows without content will be ignored in XSLX imports.
This prevents an old Excel 1.0 bug which causes openpyxl ``max_rows`` to be counting all
logical empty rows. Some editors (like LibreOffice) might add :math:`2^{20}` empty rows to the
file, which causes a significant slowdown. By default this is ``False``.

.. _exampleapp:

Example app
===========

There's an example application that showcases what import_export can do.

Before starting, set up a virtual environment ("venv") using :ref:`these instructions<create_venv>`.

You can initialize and run the example application as follows::

    cd tests
    ./manage.py makemigrations
    ./manage.py migrate
    ./manage.py createsuperuser
    ./manage.py loaddata author.json category.json book.json
    ./manage.py runserver

Go to http://127.0.0.1:8000

For example import files, see :ref:`getting_started:Test data`.

.. _logging:

Configure logging
=================

You can adjust the log level to see output as required.
This is an example configuration to be placed in your application settings::

    LOGGING = {
        "version" 1,
        "handlers": {
            "console": {"level": "DEBUG", "class": "logging.StreamHandler"},
        },
        "loggers": {
            "django.db.backends": {"level": "INFO", "handlers": ["console"]},
            "import_export": {
                "handlers": ["console"],
                "level": "INFO",
            },
        },
    }

