======================
Django import / export
======================

django-import-export is a Django application and library for importing and
exporting data with included admin integration.

**Features:**

   * support multiple formats (Excel, CSV, JSON, ...
     and everything else that `tablib`_ supports)

   * admin integration for importing

   * preview import changes

   * admin integration for exporting

   * export data respecting admin filters

   .. figure:: _static/images/django-import-export-change.png

      A screenshot of the change view with Import and Export buttons.


.. toctree::
   :maxdepth: 2
   :caption: User Guide

   installation
   getting_started
   import_workflow
   bulk_import
   celery
   changelog

.. toctree::
   :maxdepth: 2
   :caption: API documentation

   api_admin
   api_resources
   api_widgets
   api_fields
   api_instance_loaders
   api_tmp_storages
   api_results
   api_forms


.. _`tablib`: https://github.com/jazzband/tablib
