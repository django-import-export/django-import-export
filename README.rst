====================
django-import-export
====================

.. image:: https://github.com/django-import-export/django-import-export/actions/workflows/django-import-export-ci.yml/badge.svg
    :target: https://github.com/django-import-export/django-import-export/actions/workflows/django-import-export-ci.yml
    :alt: Build status on Github

.. image:: https://coveralls.io/repos/github/django-import-export/django-import-export/badge.svg?branch=main
    :target: https://coveralls.io/github/django-import-export/django-import-export?branch=main

.. image:: https://img.shields.io/pypi/v/django-import-export.svg
    :target: https://pypi.org/project/django-import-export/
    :alt: Current version on PyPi

.. image:: http://readthedocs.org/projects/django-import-export/badge/?version=stable
    :target: https://django-import-export.readthedocs.io/en/stable/
    :alt: Documentation

.. image:: https://img.shields.io/pypi/pyversions/django-import-export
    :alt: PyPI - Python Version

.. image:: https://img.shields.io/pypi/djversions/django-import-export
    :alt: PyPI - Django Version

.. image:: https://img.shields.io/badge/Contributo
    :alt: Contributor Covenant

.. image:: https://static.pepy.tech/personalized-badge/django-import-export?period=week&units=international_system&left_color=black&right_color=blue&left_text=Downloads
    :target: https://pepy.tech/project/django-import-export

django-import-export is a Django application and library for importing
and exporting data with included admin integration.

Features:

* support multiple formats (Excel, CSV, JSON, ...
  and everything else that `tablib`_ supports)

* admin integration for importing

* preview import changes

* admin integration for exporting

* export data respecting admin filters

.. image:: https://raw.githubusercontent.com/django-import-export/django-import-export/main/docs/_static/images/django-import-export-change.png


* Documentation: https://django-import-export.readthedocs.io/en/stable/
* GitHub: https://github.com/django-import-export/django-import-export/
* Free software: BSD license
* PyPI: https://pypi.org/project/django-import-export/

Example app
-----------

To run the demo app::

    cd tests
    ./manage.py makemigrations
    ./manage.py migrate
    ./manage.py createsuperuser
    ./manage.py loaddata category book
    ./manage.py runserver

Contribute
----------

Please refer to `contribution guidelines CONTRIBUTE`_.

.. _`PEP8`: https://www.python.org/dev/peps/pep-0008/
.. _`tablib`: https://github.com/jazzband/tablib
.. _`the repository`: https://github.com/django-import-export/django-import-export/
.. _CONTRIBUTE: https://django-import-export.readthedocs.io/en/latest/contributing.html