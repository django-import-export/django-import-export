=============
Bulk imports
=============

import-export provides a 'bulk mode' to improve the performance of importing large datasets.

In normal operation, import-export will call ``instance.save()`` as each row in a dataset is processed.  Bulk
mode means that ``instance.save()`` is not called, and instances are instead added to temporary lists.  Once the number
of rows processed matches the ``batch_size`` value, then either ``bulk_create()`` or ``bulk_update()`` is called.

If ``batch_size`` is set to ``None``, then ``bulk_create()`` / ``bulk_update()`` is only called once all rows have been
processed.

Bulk deletes are also supported, by applying a ``filter()`` to the temporary object list, and calling ``delete()`` on
the resulting query set.

Handling conflicts on create
============================

By default, a bulk create fails if a row conflicts with an existing row, for example because
the id is already present in the table.  This is most likely to happen when ``force_init_instance``
is enabled, because the existence check which would otherwise route the row to ``bulk_update()``
is skipped.

Set ``update_conflicts = True`` to update the conflicting row instead, making the import an upsert::

    class BookResource(ModelResource):
        class Meta:
            model = Book
            use_bulk = True
            update_conflicts = True

The fields to update default to the columns present in the dataset, except the
``import_id_fields``, the primary key and many-to-many fields.  A field whose column is
not in the dataset is left alone: with ``force_init_instance`` the row is built without
reading the stored one, so writing that field would replace the stored value with the
model default.  To update a field which a hook sets, rather than a column, declare
``update_fields``.

The conflict target defaults to the ``import_id_fields``, since those are the fields which
identify a row on import, and it must match a unique constraint on the model (the primary
key, a field declared ``unique``, or a ``UniqueConstraint`` or ``unique_together`` on exactly
those fields).  Without ``force_init_instance``, rows which match the ``import_id_fields`` are
already sent to ``bulk_update()``, so the conflicts left to handle are on another unique
field: declare it as ``unique_fields``.  Declare ``update_fields`` and ``unique_fields`` to
override either default::

    class BookResource(ModelResource):
        class Meta:
            model = Book
            use_bulk = True
            update_conflicts = True
            update_fields = ["name", "price"]
            unique_fields = ["isbn"]

These values are passed to Django's ``bulk_create()``, so its restrictions apply.  MySQL and
MariaDB do not accept a conflict target at all (they update on every unique constraint), so
``unique_fields`` is not sent on those backends.  The configuration is checked before any row
is imported: string values for ``update_fields`` or ``unique_fields``, a conflict target
without a unique constraint, an empty list of fields to update, and a backend which cannot
update conflicts are all rejected up front.

Rows which update a stored row are reported as updates, not as new rows.  Finding them takes
one query per batch, on the conflict target, before the batch is inserted.  MySQL and
MariaDB update on any unique constraint, so a row which conflicts there on a constraint other
than the conflict target is still reported as new.  The diff shown for such a row in the admin is
computed against an empty row, because the stored row is not loaded.

Caveats
=======

* The model's ``save()`` method will not be called, and ``pre_save`` and ``post_save`` signals will not be sent.

* ``bulk_update()`` is only supported in Django 2.2 upwards.

* Bulk operations do not work with many-to-many relationships.

* Take care to ensure that instances are validated before bulk operations are called.  This means ensuring that
  resource fields are declared appropriately with the correct widgets.  If an exception is raised by a bulk operation,
  then that batch will fail.  It's also possible that transactions can be left in a corrupted state.  Other batches may
  be successfully persisted, meaning that you may have a partially successful import.

* In bulk mode, exceptions are not linked to a row.  Any exceptions raised by bulk operations are logged and returned
  as critical (non-validation) errors (and re-raised if ``raise_errors`` is true).

* If there is the potential for concurrent writes to a table during a bulk operation, then you need to consider the
  potential impact of this.  Refer to :ref:`concurrent-writes` for more information.

For more information, please read the Django documentation on
`bulk_create() <https://docs.djangoproject.com/en/stable/ref/models/querysets/#bulk-create>`_ and
`bulk_update() <https://docs.djangoproject.com/en/stable/ref/models/querysets/#bulk-update>`_.

.. _foreign_key_widget_performance:

ForeignKeyWidget performance considerations
===========================================

When using :class:`~import_export.widgets.ForeignKeyWidget`, the related object is looked up using ``QuerySet.get()``
during import. This lookup occurs once per imported row.  For large imports, this can result in a significant number of
database queries and impact performance.

You can subclass ``ForeignKeyWidget`` and override ``get_queryset()`` to limit the pool of candidate objects.
However, overriding ``get_queryset()`` alone does not necessarily eliminate per-row database queries, because
``ForeignKeyWidget.clean()`` calls ``.get()`` for each row.

If import performance is critical, consider using :class:`~import_export.widgets.CachedForeignKeyWidget` instead.
This widget caches all related objects in memory before the import begins, eliminating per-row database queries.

.. _performance_tuning:

Performance tuning
==================

Consider the following if you need to improve the performance of imports.

* Enable ``use_bulk`` for bulk create, update and delete operations (read `Caveats`_ first).

* If your import is creating instances only (i.e. you are sure there are no updates), then set
  ``force_init_instance = True``.

* If your import is updating or creating instances, and you have a set of existing instances which can be stored in
  memory, use :class:`~import_export.instance_loaders.CachedInstanceLoader`

* If your import has relations on per-row basis, consider using
  :class:`~import_export.widgets.CachedForeignKeyWidget` for ForeignKey fields.

* By default, import rows are compared with the persisted representation, and the difference is stored against each row
  result.  If you don't need this diff, then disable it with ``skip_diff = True``.

* Setting ``batch_size`` to a different value is possible, but tests showed that setting this to ``None`` always
  resulted in worse performance in both duration and peak memory.

Testing
=======

Scripts are provided to enable testing and benchmarking of bulk imports.  See :ref:`testing:Bulk testing`.
