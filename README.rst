====================
django-import-export
====================

Requirements
------------

* tablib

Usage
-----

::

    >>> from core.models import Book
    >>> from import_export import resources
    >>> resource = resources.modelresource_factory(Book)()
    >>> dataset = resource.export()
    >>> print dataset.csv
    id,name,author_email,imported,published
    1,Some boook,,0,

    >>> row = list(dataset[0])
    >>> row[1] = "Rename book"
    >>> dataset.append((row))
    >>> del dataset[0]
    >>> row = list(dataset[0])
    >>> row[1] = "Book"
    >>> dataset.append((row))
    >>> del dataset[0]
    >>> result = resource.import_data(dataset, dry_run=True)
    >>> result.has_errors()
    >>> result.rows[0].diff
    [u'<span>1</span>', u'<del style="background:#ffe6e6;">Some bo</del><ins style="background:#e6ffe6;">B</ins><span>ook</span>', '', u'<span>0</span>', '']
    >>> resource.import_data(dataset)

Example app
-----------

::

    cd tests && ./manage.py runserver

Username and password for admin are 'admin', 'password'.

