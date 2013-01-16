====================
Import data workflow
====================

This document describes import data workflow, with hooks that enable
customization of import process.

``import_data`` method arguments
--------------------------------

``import_data`` method of :class:`import_export.resources.Resource` class is
responsible for import data from given `dataset`.

``import_data`` expect following arguments:

:attr:`dataset`
    REQUIRED.
    should be Tablib `Dataset`_ object with header row.

:attr:`dry_run`
    If ``True``, import should not change database. Default is ``False``.

:attr:`raise_errors`
    If ``True``, import should raise errors. Default is ``False``, which
    means that eventual errors and traceback will be saved in ``Result``
    instance.

``import_data`` method workflow
-------------------------------

#. ``import_data`` intialize new :class:`import_export.results.Result`
   instance. ``Result`` instance holds errors and other information
   gathered during import.

#. ``InstanceLoader`` responsible for loading existing instances
   is intitalized.

   Different ``InstanceLoader`` class
   can be specified with ``instance_loader_class``
   option of :class:`import_export.resources.ResourceOptions`.

   :class:`import_export.instance_loaders.CachedInstanceLoader` can be used to
   reduce number of database queries.

   See :mod:`import_export.instance_loaders` for available implementations.

#. Process each `row` in ``dataset``

   #. ``get_or_init_instance`` method is called with current ``InstanceLoader``
      and current `row` returning object `instance` and `Boolean` variable
      that indicates if object instance is new.

      ``get_or_init_instance`` tries to load instance for current `row` or
      calls ``init_instance`` to init object if object does not exists yet.

      Default ``ModelResource.init_instance`` initialize Django Model without
      arguments. You can override ``init_instance`` method to manipulate how
      new objects are initialized (ie: to set default values).

   #. ``for_delete`` method is called to determine if current `instance`
      should be deleted:

      #. current `instance` is deleted
 
      OR
 
      #. ``import_obj`` method is called with current object `instance` and
         current `row`.
 
         ``import_obj`` loop through all `Resource` `fields`, skipping
         many to many fields and calls ``import_field`` for each. (Many to many
         fields require that instance have a primary key, this is why assigning
         them is postponed, after object is saved).
 
         ``import_field`` calls ``field.save`` method, if ``field`` has
         both `attribute` and field `column_name` exists in given row.
 
      #. ``save_instance`` method is called.
 
         ``save_instance`` receives ``dry_run`` argument and actually saves
         instance only when ``dry_run`` is False.
 
         ``save_instance`` calls two hooks methods that by default does not
         do anything but can be overriden to customize import process:
 
         * ``before_save_instance``
 
         * ``after_save_instance``
 
         Both methods receive ``instance`` and ``dry_run`` arguments.
 
      #. ``save_m2m`` method is called to save many to many fields.
 
   #. ``RowResult`` is assigned with diff between original and imported
       object fields as well as import type(new, updated).
 
       If exception is raised inside row processing, and ``raise_errors`` is
       ``False`` (default), traceback is appended to ``RowResult``.

#. ``result`` is returned.

.. _Dataset: http://docs.python-tablib.org/en/latest/api/#dataset-object
