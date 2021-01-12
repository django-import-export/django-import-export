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

You can configure the following in your settings file:

``IMPORT_EXPORT_USE_TRANSACTIONS``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Controls if resource importing should use database transactions. Defaults to
``False``. Using transactions makes imports safer as a failure during import
won’t import only part of the data set.

Can be overridden on a ``Resource`` class by setting the
``use_transactions`` class attribute.

``IMPORT_EXPORT_SKIP_ADMIN_LOG``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If set to ``True``, skips the creation of admin log entries when importing.
Defaults to ``False``. This can speed up importing large data sets, at the cost
of losing an audit trail.

Can be overridden on a ``ModelAdmin`` class inheriting from ``ImportMixin`` by
setting the ``skip_admin_log`` class attribute.

``IMPORT_EXPORT_TMP_STORAGE_CLASS``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Controls which storage class to use for storing the temporary uploaded file
during imports. Defaults to ``import_export.tmp_storages.TempFolderStorage``.

Can be overridden on a ``ModelAdmin`` class inheriting from ``ImportMixin`` by
setting the ``tmp_storage_class`` class attribute.

``IMPORT_EXPORT_IMPORT_PERMISSION_CODE``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If set, lists the permission code that is required for users to perform the
“import” action. Defaults to ``None``, which means everybody can perform
imports.

Django’s built-in permissions have the codes ``add``, ``change``, ``delete``,
and ``view``. You can also add your own permissions.

``IMPORT_EXPORT_EXPORT_PERMISSION_CODE``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If set, lists the permission code that is required for users to perform the
“export” action. Defaults to ``None``, which means everybody can perform
exports.

Django’s built-in permissions have the codes ``add``, ``change``, ``delete``,
and ``view``. You can also add your own permissions.

``IMPORT_EXPORT_CHUNK_SIZE``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

An integer that defines the size of chunks when iterating a QuerySet for data
exports. Defaults to ``100``. You may be able to save memory usage by
decreasing it, or speed up exports by increasing it.

Can be overridden on a ``Resource`` class by setting the ``chunk_size`` class
attribute.


Example app
===========

There's an example application that showcases what django-import-export can do.
It's assumed that you have set up a Python ``venv`` with all required dependencies
or are otherwise able to run Django locally.

You can run it via::

    cd tests
    ./manage.py makemigrations
    ./manage.py migrate
    ./manage.py createsuperuser
    ./manage.py loaddata category.json book.json
    ./manage.py runserver

Go to http://127.0.0.1:8000

``books-sample.csv`` contains sample book data which can be imported.
