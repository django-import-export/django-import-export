=============
Release Notes
=============

v4
==

v4 of import-export (released Q4 2023) contains a number of minor changes to the API.

If you have customized import-export by overriding methods, then you will have to
modify your installation before working with v4.  If you have not overridden any
methods then you should not be affected by these changes and no changes to your code
should be necessary.

In both cases, please test thoroughly before deploying v4 to production.

Refer to
`this PR <https://github.com/django-import-export/django-import-export/pull/1641/>`_
for more information.

This guide describes the major changes and how to upgrade.

API changes
===========

The API changes mostly change method arguments, although some method names have changed.

Methods which process row data have been updated so that method args are standardized.
This has been done to resolve inconsistency issues where the parameters differed between
method calls, and to allow easier extensibility.

:class:`import_export.resources.Resource`
-----------------------------------------

Renamed methods
^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1

   * - Previous
     - New
     - Summary

   * - ``import_obj(self, obj, data, dry_run, **kwargs)``
     - ``import_instance(self, instance, row, **kwargs)``
     -  * ``obj`` param renamed to ``instance``
        * ``data`` param renamed to ``row``
        * ``dry_run`` param now in ``kwargs``

   * - ``after_import_instance(self, instance, new, row_number=None, **kwargs)``
     - ``after_init_instance(self, instance, new, row, **kwargs)``
     -  * ``row`` added as mandatory arg
        * ``row_number`` now in ``kwargs``

Parameter changes
^^^^^^^^^^^^^^^^^

This section describes methods in which the parameters have changed.

.. list-table::
   :header-rows: 1

   * - Previous
     - New
     - Summary

   * - ``before_import(self, dataset, using_transactions, dry_run, **kwargs)``
     - ``before_import(self, dataset, **kwargs)``
     -  * ``using_transactions`` param now in ``kwargs``
        * ``dry_run`` param now in ``kwargs``

   * - ``after_import(self, dataset, result, using_transactions, dry_run, **kwargs)``
     - ``after_import(self, dataset, result, **kwargs)``
     -  * ``using_transactions`` param now in ``kwargs``
        * ``dry_run`` param now in ``kwargs``

   * - ``before_import_row(self, row, row_number=None, **kwargs)``
     - ``before_import_row(self, row, **kwargs)``
     - * ``row_number`` now in ``kwargs``

   * - ``after_import_row(self, row, row_result, row_number=None, **kwargs)``
     - ``after_import_row(self, row, row_result, **kwargs)``
     - * ``row_number`` now in ``kwargs``

   * - ``import_row(self, row, instance_loader, using_transactions=True, dry_run=False, **kwargs)``
     - ``import_row(self, row, instance_loader, **kwargs)``
     - * ``dry_run`` param now in ``kwargs``
       * ``using_transactions`` param now in ``kwargs``

   * - ``save_instance(self, instance, is_create, using_transactions=True, dry_run=False)``
     - ``save_instance(self, instance, is_create, row, ***kwargs)``
     - * ``dry_run`` param now in ``kwargs``
       * ``using_transactions`` param now in ``kwargs``
       * ``row`` added as mandatory arg

   * - ``save_m2m(self, obj, data, using_transactions, dry_run)``
     - ``save_m2m(self, instance, row, **kwargs)``
     - * ``dry_run`` param now in ``kwargs``
       * ``using_transactions`` param now in ``kwargs``
       * ``row`` added as mandatory arg
       * ``obj`` renamed to ``instance``
       * ``data`` renamed to ``row``

   * - ``before_save_instance(self, instance, using_transactions, dry_run)``
     - ``before_save_instance(self, instance, row, **kwargs)``
     - * ``dry_run`` param now in ``kwargs``
       * ``using_transactions`` param now in ``kwargs``
       * ``row`` added as mandatory arg

   * - ``after_save_instance(self, instance, using_transactions, dry_run)``
     - ``after_save_instance(self, instance, row, **kwargs)``
     - * ``dry_run`` param now in ``kwargs``
       * ``using_transactions`` param now in ``kwargs``
       * ``row`` added as mandatory arg

   * - ``delete_instance(self, instance, using_transactions=True, dry_run=False)``
     - ``delete_instance(self, instance, row, **kwargs)``
     - * ``dry_run`` param now in ``kwargs``
       * ``using_transactions`` param now in ``kwargs``
       * ``row`` added as mandatory arg

   * - ``before_delete_instance(self, instance, dry_run)``
     - ``before_delete_instance(self, instance, row, **kwargs)``
     - * ``dry_run`` param now in ``kwargs``
       * ``using_transactions`` param now in ``kwargs``
       * ``row`` added as mandatory arg

   * - ``after_delete_instance(self, instance, dry_run)``
     - ``after_delete_instance(self, instance, row, **kwargs)``
     - * ``dry_run`` param now in ``kwargs``
       * ``using_transactions`` param now in ``kwargs``
       * ``row`` added as mandatory arg

   * - ``before_export(self, queryset, *args, **kwargs)``
     - ``before_export(self, queryset, **kwargs)``
     - * unused ``*args`` list removed

   * - ``after_export(self, queryset, data, *args, **kwargs)``
     - ``after_export(self, queryset, dataset, **kwargs)``
     - * unused ``*args`` list removed
       * ``data`` renamed to ``dataset``

   * - ``filter_export(self, queryset, *args, **kwargs)``
     - ``filter_export(self, queryset, **kwargs)``
     - * unused ``*args`` list removed

   * - ``export_field(self, field, obj)``
     - ``export_field(self, field, instance)``
     - * ``obj`` renamed to ``instance``

   * - ``export(self, *args, queryset=None, **kwargs)``
     - ``export(self, queryset=None, **kwargs)``
     - * unused ``*args`` list removed

:class:`import_export.mixins.BaseImportMixin`
---------------------------------------------

Parameter changes
^^^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1

   * - Previous
     - New
     - Summary

   * - ``get_import_resource_kwargs(self, request, *args, **kwargs)``
     - ``get_import_resource_kwargs(self, request, **kwargs)``
     -  * ``using_transactions`` param now in ``kwargs``
        * ``dry_run`` param now in ``kwargs``
        * unused ``*args`` list removed


:class:`import_export.mixins.BaseExportMixin`
---------------------------------------------

Parameter changes
^^^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1

   * - Previous
     - New
     - Summary

   * - ``get_export_resource_kwargs(self, request, *args, **kwargs)``
     - ``get_export_resource_kwargs(self, request, **kwargs)``
     -  * unused ``*args`` list removed

   * - ``get_export_resource_kwargs(self, request, *args, **kwargs)``
     - ``get_export_resource_kwargs(self, request, **kwargs)``
     -  * unused ``*args`` list removed

   * - ``get_data_for_export(self, request, *args, **kwargs)``
     - ``get_data_for_export(self, request, queryset, **kwargs)``
     -  * unused ``*args`` list removed


:class:`import_export.fields.Field`
-----------------------------------

Parameter changes
^^^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1

   * - Previous
     - New
     - Summary

   * - ``clean(self, data, **kwargs)``
     - ``clean(self, row, **kwargs)``
     - * ``data`` renamed to ``row``

   * - ``get_value(self, instance)``
     - ``get_value(self, obj)``
     - * ``obj`` renamed to ``instance``

   * - ``save(self, obj, data, is_m2m=False, **kwargs)``
     - ``save(self, instance, row, is_m2m=False, **kwargs)``
     - * ``obj`` renamed to ``instance``
       * ``data`` renamed to ``row``

   * - ``export(self, obj)``
     - ``export(self, instance)``
     - * ``obj`` renamed to ``instance``
