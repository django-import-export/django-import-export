====================
django-import-export
====================

.. image:: https://travis-ci.org/django-import-export/django-import-export.svg?branch=master
    :target: https://travis-ci.org/django-import-export/django-import-export
    :alt: Build status on Travis-CI

.. image:: https://coveralls.io/repos/github/django-import-export/django-import-export/badge.svg?branch=coveralls
    :target: https://coveralls.io/github/django-import-export/django-import-export?branch=coveralls

.. image:: https://img.shields.io/pypi/v/django-import-export.svg
    :target: https://pypi.org/project/django-import-export/
    :alt: Current version on PyPi

.. image:: http://readthedocs.org/projects/django-import-export/badge/?version=stable
    :target: https://django-import-export.readthedocs.io/en/stable/
    :alt: Documentation

django-import-export is a Django application and library for importing
and exporting data with included admin integration.

Features:

* support multiple formats (Excel, CSV, JSON, ...
  and everything else that `tablib`_ support)

* admin integration for importing

* preview import changes

* admin integration for exporting

* export data respecting admin filters

.. image:: docs/_static/images/django-import-export-change.png


* Documentation: https://django-import-export.readthedocs.io/en/stable/
* GitHub: https://github.com/django-import-export/django-import-export/
* Free software: BSD license
* PyPI: https://pypi.org/project/django-import-export/

Requirements
-----------

* Python 2.7+ or Python 3.3+
* Django 1.8+
* tablib (dev or 0.9.11)

Example app
-----------

::

    cd tests && ./manage.py runserver

Username and password for admin are 'admin', 'password'.

Contribute
----------

If you'd like to contribute, simply fork `the repository`_, commit your
changes to the **develop** branch (or branch off of it), and send a pull
request. Make sure you add yourself to AUTHORS_.

As most projects, we try to follow PEP8_ as closely as possible. Please bear
in mind that most pull requests will be rejected without proper unit testing.

.. _`PEP8`: https://www.python.org/dev/peps/pep-0008/
.. _`tablib`: https://github.com/kennethreitz/tablib
.. _`the repository`: https://github.com/django-import-export/django-import-export/
.. _AUTHORS: https://github.com/django-import-export/django-import-export/blob/master/AUTHORS
