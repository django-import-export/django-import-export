====================
django-import-export
====================

.. image:: https://travis-ci.org/django-import-export/django-import-export.svg?branch=master
    :target: https://travis-ci.org/django-import-export/django-import-export
.. image:: https://img.shields.io/pypi/v/django-import-export.svg
    :target: https://pypi.python.org/pypi/django-import-export
.. image:: https://img.shields.io/pypi/dm/django-import-export.svg
        :target: https://pypi.python.org/pypi/django-import-export    

django-import-export is a Django application and library for importing
and exporting data with included admin integration.

Features:

* support multiple formats (Excel, CSV, JSON, ...
  and everything else that `tablib`_ support)

* admin integration for importing

* preview import changes

* admin integration for exporting

* export data respecting admin filters

.. image:: https://raw.github.com/django-import-export/django-import-export/master/docs/_static/images/django-import-export-change.png


* Documentation: https://django-import-export.readthedocs.org/en/latest/
* GitHub: https://github.com/django-import-export/django-import-export/
* Free software: BSD license
* PyPI: https://pypi.python.org/pypi/django-import-export/

Requirements
-----------

* Python 2.7+ or Python 3.3+
* Django 1.4.2+
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

.. _`tablib`: https://github.com/kennethreitz/tablib
.. _`the repository`: https://github.com/django-import-export/django-import-export/
.. _AUTHORS: https://github.com/django-import-export/django-import-export/blob/master/AUTHORS
