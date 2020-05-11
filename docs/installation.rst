==============================
Installation and configuration
==============================

django-import-export is available on the Python Package Index (PyPI), so it
can be installed with standard Python tools like ``pip`` or ``easy_install``::

    $ pip install django-import-export

This will automatically install many formats supported by tablib. If you need
additional formats like ``cli`` or ``Pandas DataFrame``, you should install the
appropriate tablib dependencies (e.g. ``pip install tablib[pandas]``). Read
more on the `tablib format documentation page`_.

.. _tablib format documentation page: https://tablib.readthedocs.io/en/stable/formats/

Alternatively, you can install the git repository directly to obtain the
development version::

    $ pip install -e git+https://github.com/django-import-export/django-import-export.git#egg=django-import-export

Now, you're good to go, unless you want to use django-import-export from the
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
django-import-export in your project.



Settings
========

You can use the following directives in your settings file:

``IMPORT_EXPORT_USE_TRANSACTIONS``
    Global setting controls if resource importing should use database
    transactions. Default is ``False``.

``IMPORT_EXPORT_SKIP_ADMIN_LOG``
    Global setting controls if creating log entries for the admin changelist
    should be skipped when importing resource. The `skip_admin_log` attribute
    of `ImportMixin` is checked first, which defaults to ``None``. If not
    found, this global option is used. This will speed up importing large
    datasets, but will lose changing logs in the admin changelist view.
    Default is ``False``.

``IMPORT_EXPORT_TMP_STORAGE_CLASS``
    Global setting for the class to use to handle temporary storage of the
    uploaded file when importing from the admin using an `ImportMixin`.  The
    `tmp_storage_class` attribute of `ImportMixin` is checked first, which
    defaults to ``None``. If not found, this global option is used. Default is
    ``TempFolderStorage``.

``IMPORT_EXPORT_IMPORT_PERMISSION_CODE``
    Global setting for defining user permission that is required for
    users/groups to execute import action. Django builtin permissions are
    ``change``, ``add``, and ``delete``. It is possible to add your own
    permission code. Default is ``None`` which means everybody can execute
    import action.

``IMPORT_EXPORT_EXPORT_PERMISSION_CODE``
    Global setting for defining user permission that is required for
    users/groups to execute export action. Django builtin permissions are
    ``change``, ``add``, and ``delete``. It is possible to add your own
    permission code. Default is ``None`` which means everybody can execute
    export action.

``IMPORT_EXPORT_CHUNK_SIZE``
    Global setting to define the bulk size in which data is exported. Useful
    if memory consumption is of the essence. Can also be set per ``Resource``


Example app
===========

There's an example application that showcases what django-import-export can do.
It's assumed that you have set up a Python ``venv`` with all required dependencies
or are otherwise able to run Django locally.

You can run it via::

    cd tests
    ./manage.py makemigration
    ./manage.py migrate
    ./manage.py createsuperuser
    ./manage.py loaddata category.json book.json
    ./manage.py runserver

Go to http://127.0.0.1:8000

``books-sample.csv`` contains sample book data which can be imported.
