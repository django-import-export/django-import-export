================
v4 upgrade guide
================

v4 of import-export (released Q4 2023) contains a number of minor changes to the API.

Refer to
`this PR <https://github.com/django-import-export/django-import-export/pull/1641/>`_
for more information.

If you have customized import-export by overriding methods, then you will have to
modify your installation before working with v4.  If you have not overridden any
methods then you should not be affected by these changes and no changes to your code
should be necessary.

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

The following internal methods have been renamed:

- `import_obj()` now renamed to `import_instance(self, instance, new, row, **kwargs)`

  - `obj` param renamed to `instance`

  - `data` param renamed to `row`

  - `dry_run` param now in `kwargs`

- `after_import_instance()` renamed to `after_init_instance(self, instance, new, row, **kwargs)`

  - `row` added as mandatory arg

  - `row_number` now in `kwargs`

Parameter changes
^^^^^^^^^^^^^^^^^

This section describes methods in which the parameters have changed.

- `before_import(self, dataset, **kwargs)`

  - `using_transactions` param now in `kwargs`

  - `dry_run` param now in `kwargs`

- `after_import(self, dataset, result, **kwargs)`

  - `using_transactions` param now in `kwargs`

  - `dry_run` param now in `kwargs`

- `before_import_row(self, row, **kwargs)`

  - `row_number` now in `kwargs`

- `after_import_row(self, row, row_result, **kwargs)`

  - `row_number` now in `kwargs`

- `import_row(self, row, instance_loader, **kwargs)`

  - `using_transactions` param now in `kwargs`

  - `dry_run` param now in `kwargs`

  - `row_number` now in `kwargs`

- `save_instance(self, instance, is_create, row, **kwargs)`

  - `row` added as mandatory arg

  - `using_transactions` and `dry_run` named parameters are now in the `kwargs` dict

- `save_m2m(instance, row, **kwargs)`

  - `obj` param renamed to `instance`

  - `data` param renamed to `row`

  - `using_transactions` param now in `kwargs`

  - `dry_run` param now in `kwargs`

- `save_instance(self, instance, is_create, row, **kwargs)`

  - `row` added as mandatory arg

  - `using_transactions` param now in `kwargs`

  - `dry_run` param now in `kwargs`

- `before_save_instance(self, instance, row, **kwargs)`

  - `row` added as mandatory arg

  - `using_transactions` param now in `kwargs`

  - `dry_run` param now in `kwargs`

- `after_save_instance(self, instance, row, **kwargs)`

  - `row` added as mandatory arg

  - `using_transactions` param now in `kwargs`

  - `dry_run` param now in `kwargs`

- `delete_instance(self, instance, row, **kwargs)`

  - `row` added as mandatory arg

  - `using_transactions` param now in `kwargs`

  - `dry_run` param now in `kwargs`

- `before_delete_instance(self, instance, row, **kwargs)`

  - `row` added as mandatory arg

  - `dry_run` param now in `kwargs`

- `after_delete_instance(self, instance, row, **kwargs)`

  - `row` added as mandatory arg

  - `dry_run` param now in `kwargs`

- `before_export(self, queryset, **kwargs)`

  - unused `*args` list removed

- `after_export(self, queryset, dataset, **kwargs)`

  - `data` renamed to `dataset`

  - unused `*args` list removed

- `filter_export(self, queryset, **kwargs)`

  - unused `*args` list removed

- `export_field(self, field, instance)`

  - `obj` renamed to `instance`

- `export(self, queryset=None, **kwargs)`

  - unused `*args` list removed

- `import_field(self, field, instance, row, is_m2m=False, **kwargs)`

  - `obj` param renamed to `instance`

  - `data` param renamed to `row`

:class:`import_export.mixins.BaseImportMixin`
---------------------------------------------

Parameter changes
^^^^^^^^^^^^^^^^^

- `get_import_resource_kwargs(self, request, **kwargs)`

  - unused `*args` list removed

:class:`import_export.mixins.BaseExportMixin`
---------------------------------------------

Parameter changes
^^^^^^^^^^^^^^^^^

- `get_export_resource_kwargs(self, request, **kwargs)`

  - unused `*args` list removed

- `get_data_for_export(self, request, queryset, **kwargs)`

  - unused `*args` list removed

:class:`import_export.fields.Field`
-----------------------------------

Parameter changes
^^^^^^^^^^^^^^^^^

- `clean(self, row, **kwargs)`

  - `data` renamed to `row`

- `get_value(self, instance)`

  - `obj` renamed to `instance`

- `save(self, instance, row, is_m2m=False, **kwargs)`

  - `obj` renamed to `instance`

  - `data` renamed to `row`

- `export(self, instance)`

  - `obj` renamed to `instance`
