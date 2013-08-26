====================
django-import-export
====================

.. image:: https://travis-ci.org/bmihelac/django-import-export.png?branch=master
        :target: https://travis-ci.org/bmihelac/django-import-export
.. image:: https://pypip.in/d/django-import-export/badge.png
    :target: https://crate.io/packages/django-import-export
.. image:: https://pypip.in/v/django-import-export/badge.png   
    :target: https://crate.io/packages/django-import-export

django-import-export is a Django application and library for importing
and exporting data with included admin integration.

Features:

* support multiple formats (Excel, CSV, JSON, ...
  and everything else that `tablib`_ support)

* admin integration for importing

* preview import changes

* admin integration for exporting

* export data respecting admin filters

.. image:: https://raw.github.com/bmihelac/django-import-export/master/docs/_static/images/django-import-export-change.png

Documentation
-------------

https://django-import-export.readthedocs.org/en/latest/

Example app
-----------

::

    cd tests && ./manage.py runserver

Username and password for admin are 'admin', 'password'.


.. _`tablib`: https://github.com/kennethreitz/tablib
