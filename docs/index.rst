======================
Django import / export
======================

django-import-export is a Django application and library for importing and
exporting data with included admin integration.

**Features:**

   * Import from / Export to multiple file formats

   * Manage import / export of object relations, data types

   * Handle create / update / delete / skip during imports

   * Extensible API

   * Support multiple formats (Excel, CSV, JSON, ...
     and everything else that `tablib`_ supports)

   * Bulk import

   * Admin integration for importing / exporting

     * Preview import changes

     * Export data respecting admin filters

   .. figure:: _static/images/django-import-export-change.png

      A screenshot of the change view with Import and Export buttons.


.. toctree::
   :maxdepth: 2
   :caption: User Guide

   installation
   getting_started
   advanced_usage
   admin_integration
   import_workflow
   export_workflow
   bulk_import
   management_commands
   celery
   testing
   faq
   screenshots
   release_notes
   changelog

.. toctree::
   :maxdepth: 2
   :caption: API documentation

   api_admin
   api_resources
   api_widgets
   api_fields
   api_instance_loaders
   api_mixins
   api_tmp_storages
   api_results
   api_forms
   api_exceptions

.. toctree::
   :maxdepth: 2
   :caption: Developers

   contributing


.. _`tablib`: https://github.com/jazzband/tablib
