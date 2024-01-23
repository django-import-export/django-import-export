=============
Release Notes
=============

v4
==

v4 introduces significant updates to import-export.  We have taken the opportunity to introduce
breaking changes in order to fix some long-standing issues.

Refer to the :doc:`changelog<changelog>` for more information. Please ensure you test
thoroughly before deploying v4 to production.

This guide describes the major changes and how to upgrade.

Installation
============

We have modified installation methods to allow for optional dependencies.
This means that you have to explicitly declare dependencies when installing import-export.

If you are not sure, or want to preserve the pre-v4 behaviour, then ensure that
import-export is installed as follows (either in your requirements file or during
installation)::

  django-import-export[all]

Functional changes
==================

CharWidget
----------

:meth:`~import_export.widgets.CharWidget.clean` will now return a string type as the default.
The ``coerce_to_string`` option introduced in v3 is no longer used in this method.

Validation error messages
-------------------------

The following widgets have had validation error messages updated:

* :class:`~import_export.widgets.DateWidget`
* :class:`~import_export.widgets.TimeWidget`
* :class:`~import_export.widgets.DateTimeWidget`
* :class:`~import_export.widgets.DurationWidget`

Export format
-------------

We have standardized the export output which is returned from
:meth:`~import_export.widgets.Widget.render`.

Prior to v4, the export format returned from ``render()`` varied between Widget implementations.
In v4, return values are rendered as strings by default (where applicable), with
``None`` values returned as empty strings.  Widget params can modify this behavior.

Refer to the :doc:`documentation<api_widgets>` for more information.

Export field order
------------------

The ordering rules for exported fields has been standardized. See :ref:`documentation<field_ordering>`.

Error output
------------

If the ``raise_errors`` parameter of :meth:`~import_export.resources.Resource.import_data` is ``True``, then an instance
of :class:`~import_export.exceptions.ImportError` is raised.  This exception wraps the underlying exception.

See `this PR <https://github.com/django-import-export/django-import-export/issues/1729>`_.

Deprecations
============

* The ``obj`` param passed to :meth:`~import_export.widgets.Widget.render` is deprecated.
  The :meth:`~import_export.widgets.Widget.render` method should not need to have a reference to
  model instance.

* Use of ``ExportViewFormMixin`` is deprecated.  See `this issue <https://github.com/django-import-export/django-import-export/issues/1666>`_.

* See :ref:`renamed_methods`.

Admin UI
========

LogEntry
--------

``LogEntry`` instances are created during import for creates, updates and deletes.
The functionality to store ``LogEntry`` has changed in v4 in order to address a deprecation in Django 5.
For this to work correctly, deleted instances are now always copied and retained in each
:class:`~import_export.results.RowResult` so that they can be recorded in each ``LogEntry``.

This only occurs for delete operations initiated from the Admin UI.

Export action
-------------

The export action has been updated to include the export workflow.  Prior to v4, it was possible to select export
selected items using an export admin action.  However this meant that the export workflow was skipped and it was not
possible to select the export resource.  This has been fixed in v4 so that export workflow is now present when
exporting via the Admin UI action.  For more information see :ref:`export documentation<export_via_admin_action>`.

Export selected fields
----------------------

The :ref:`export 'confirm' page<export_confirm>` now includes selectable fields for export.
If you wish to revert to the previous (v3) version of the export confirm screen, add a
:attr:`~import_export.admin.ExportMixin.export_form_class` declaration to your Admin class subclass, for example::

  class BookAdmin(ImportExportModelAdmin):
    export_form_class = ExportForm

Success message
---------------

The success message shown on successful import has been updated to include the number of 'deleted' and 'skipped' rows.
See `this PR <https://github.com/django-import-export/django-import-export/issues/1691>`_.

Import error messages
---------------------

The default error message for import errors has been modified to simplify the format.
Error messages now contain the error message only by default.  The row and traceback are not presented.

The original format can be restored by setting :attr:`~import_export.admin.ImportMixin.import_error_display` on the
Admin class definition.  For example::

  class BookAdmin(ImportExportModelAdmin):
    import_error_display = ("message", "row", "traceback")


See `this issue <https://github.com/django-import-export/django-import-export/issues/1724>`_.

API changes
===========

v4 of import-export contains a number of minor changes to the API.

If you have customized import-export by overriding methods, then you will have to
modify your installation before working with v4.  If you have not overridden any
methods then you should not be affected by these changes and no changes to your code
should be necessary.

The API changes include changes to method arguments, although some method names have
changed.

Refer to
`this PR <https://github.com/django-import-export/django-import-export/pull/1641/>`_
for more information.

Methods which process row data have been updated so that method args are standardized.
This has been done to resolve inconsistency issues where the parameters differed between
method calls, and to allow easier extensibility.

:class:`import_export.resources.Resource`
-----------------------------------------

.. _renamed_methods:

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
     - * ``row`` added as mandatory arg
       * ``obj`` renamed to ``instance``
       * ``data`` renamed to ``row``
       * ``dry_run`` param now in ``kwargs``
       * ``using_transactions`` param now in ``kwargs``

   * - ``before_save_instance(self, instance, using_transactions, dry_run)``
     - ``before_save_instance(self, instance, row, **kwargs)``
     - * ``row`` added as mandatory arg
       * ``dry_run`` param now in ``kwargs``
       * ``using_transactions`` param now in ``kwargs``

   * - ``after_save_instance(self, instance, using_transactions, dry_run)``
     - ``after_save_instance(self, instance, row, **kwargs)``
     - * ``row`` added as mandatory arg
       * ``dry_run`` param now in ``kwargs``
       * ``using_transactions`` param now in ``kwargs``

   * - ``delete_instance(self, instance, using_transactions=True, dry_run=False)``
     - ``delete_instance(self, instance, row, **kwargs)``
     - * ``row`` added as mandatory arg
       * ``dry_run`` param now in ``kwargs``
       * ``using_transactions`` param now in ``kwargs``

   * - ``before_delete_instance(self, instance, dry_run)``
     - ``before_delete_instance(self, instance, row, **kwargs)``
     - * ``row`` added as mandatory arg
       * ``dry_run`` param now in ``kwargs``
       * ``using_transactions`` param now in ``kwargs``

   * - ``after_delete_instance(self, instance, dry_run)``
     - ``after_delete_instance(self, instance, row, **kwargs)``
     - * ``row`` added as mandatory arg
       * ``dry_run`` param now in ``kwargs``
       * ``using_transactions`` param now in ``kwargs``

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


:class:`import_export.forms.ImportExportFormBase`
-------------------------------------------------

If you have subclassed one of the :mod:`~import_export.forms` then you may need to
modify the parameters passed to constructors.

The ``input_format`` field of :class:`~import_export.forms.ImportForm` has been moved to the parent class
(:class:`~import_export.forms.ImportExportFormBase`) and renamed to ``format``.

Parameter changes
^^^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1

   * - Previous
     - New
     - Summary

   * - ``__init__(self, *args, resources=None, **kwargs)``
     - ``__init__(self, formats, resources, *args, **kwargs)``
     - * ``formats`` added as a mandatory arg
       * ``resources`` added as a mandatory arg
