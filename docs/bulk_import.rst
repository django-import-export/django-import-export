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

* If you use :class:`~import_export.widgets.ForeignKeyWidget` then this should not affect performance during lookups,
  because the ``QuerySet`` cache should be used.  Some more information
  `here <https://stackoverflow.com/a/78309357/39296>`_.

* If there is the potential for concurrent writes to a table during a bulk operation, then you need to consider the
  potential impact of this.  Refer to :ref:`concurrent-writes` for more information.

For more information, please read the Django documentation on
`bulk_create() <https://docs.djangoproject.com/en/stable/ref/models/querysets/#bulk-create>`_ and
`bulk_update() <https://docs.djangoproject.com/en/stable/ref/models/querysets/#bulk-update>`_.

.. _performance_tuning
Performance tuning
==================

Consider the following if you need to improve the performance of imports.

* Enable ``use_bulk`` for bulk create, update and delete operations (read `Caveats`_ first).

* If your import is creating instances only (i.e. you are sure there are no updates), then set
  ``force_init_instance = True``.

* If your import is updating or creating instances, and you have a set of existing instances which can be stored in
  memory, use :class:`~import_export.instance_loaders.CachedInstanceLoader`

* By default, import rows are compared with the persisted representation, and the difference is stored against each row
  result.  If you don't need this diff, then disable it with ``skip_diff = True``.

* Setting ``batch_size`` to a different value is possible, but tests showed that setting this to ``None`` always
  resulted in worse performance in both duration and peak memory.

Testing
=======

Scripts are provided to enable testing and benchmarking of bulk imports.  See :ref:`testing:Bulk testing`.
