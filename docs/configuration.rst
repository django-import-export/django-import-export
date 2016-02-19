Configuration
=============

You only need to perform this configuration step if you use
 django-import-export in the admin.

Add ``import_export`` to your ``INSTALLED_APPS``:

    INSTALLED_APPS = [
        # ...
        'import_export',
    ]

Deploy static files:

    $ python manage.py collectstatic
