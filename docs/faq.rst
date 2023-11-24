==========================
Frequently Asked Questions
==========================

What's the best way to communicate a problem, question, or suggestion?
======================================================================

To submit a feature, to report a bug, or to ask a question, please refer our
:doc:`contributing guidelines <contributing>`.

How can I help?
===============

We welcome contributions from the community.

You can help in the following ways:

* Reporting bugs or issues.

* Answering questions which arise on Stack Overflow or as Github issues.

* Providing translations for UI text.

* Suggesting features or changes.

We encourage you to read the :doc:`contributing guidelines <contributing>`.

.. _common_issues:

Common issues
=============

key error 'id' in ``get_import_id_fields()``
--------------------------------------------

When attempting to import, this error can be seen.  This indicates that the ``Resource`` has not been configured
correctly, and the import logic fails.  Specifically, the import process is looking for an instance field called ``id``
and there is no such field in the import.  See :ref:`advanced_usage:Create or update model instances`.

How to handle double-save from Signals
--------------------------------------

This issue can apply if you have implemented post-save :ref:`advanced_usage:signals`, and you are using the import workflow in the Admin
interface.  You will find that the post-save signal is called twice for each instance.  The reason for this is that
the model ``save()`` method is called twice: once for the 'confirm' step and once for the 'import' step.  The call
to ``save()`` during the 'confirm' step is necessary to prove that the object will be saved successfully, or to
report any exceptions in the Admin UI if save failed.  After the 'confirm' step, the database transaction is rolled
back so that no changes are persisted.

Therefore there is no way at present to stop ``save()`` being called twice, and there will always be two signal calls.
There is a workaround, which is to set a temporary flag on the instance being saved::

    class BookResource(resources.ModelResource):

        def before_save_instance(self, instance, row, **kwargs):
            # during 'confirm' step, dry_run is True
            instance.dry_run = kwargs.get("dry_run", False)

        class Meta:
            model = Book
            fields = ('id', 'name')

Your signal receiver can then include conditional logic to handle this flag::

    @receiver(post_save, sender=Book)
    def my_callback(sender, **kwargs):
        instance = kwargs["instance"]
        if getattr(instance, "dry_run"):
            # no-op if this is the 'confirm' step
            return
        else:
            # your custom logic here
            # this will be executed only on the 'import' step
            pass

Further discussion `here <https://github.com/django-import-export/django-import-export/issues/1078/>`_
and `here <https://stackoverflow.com/a/71625152/39296/>`_.


How to dynamically set resource values
--------------------------------------

There can be use cases where you need a runtime or user supplied value to be passed to a Resource.
See :ref:`dynamically_set_resource_values`.

How to set a value on all imported instances prior to persisting
----------------------------------------------------------------

If you need to set the same value on each instance created during import then refer to
:ref:`advanced_usage:How to set a value on all imported instances prior to persisting`.

How to export from more than one table
--------------------------------------

In the usual configuration, a ``Resource`` maps to a single model.  If you want to export data associated with
relations to that model, then these values can be defined in the ``fields`` declaration.
See :ref:`advanced_usage:Model relations`.

How to import imagefield in excel cell
--------------------------------------

Please refer to `this issue <https://github.com/django-import-export/django-import-export/issues/90>`_.

How to hide stack trace in UI error messages
--------------------------------------------

Please refer to `this issue <https://github.com/django-import-export/django-import-export/issues/1257#issuecomment-952276485>`_.

Ids incremented twice during import
-----------------------------------

When importing using the Admin site, it can be that the ids of the imported instances are different from those show
in the preview step.  This occurs because the rows are imported during 'confirm', and then the transaction is rolled
back prior to the confirm step.  Database implementations mean that sequence numbers may not be reused.

Consider enabling :ref:`import_export_skip_admin_confirm` as a workaround.

See `this issue <https://github.com/django-import-export/django-import-export/issues/560>`_ for more detailed
discussion.

Not Null constraint fails when importing blank Charfield
--------------------------------------------------------

See `this issue <https://github.com/django-import-export/django-import-export/issues/1485>`_.

Foreign key is null when importing
----------------------------------

It is possible to reference model relations by defining a field with the double underscore syntax. For example::

  fields = ("author__name")

This means that during export, the relation will be followed and the referenced field will be added correctly to the
export.

This does not work during import because the reference may not be enough to identify the correct relation instance.
:class:`~import_export.widgets.ForeignKeyWidget` should be used during import.  See the documentation explaining
:ref:`advanced_usage:Foreign Key relations`.

How to customize export data
----------------------------

See the following responses on StackOverflow:

  * https://stackoverflow.com/a/55046474/39296
  * https://stackoverflow.com/questions/74802453/export-only-the-data-registered-by-the-user-django-import-export

How to set export file encoding
-------------------------------

If export produces garbled or unexpected output, you may need to set the export encoding.
See `this issue <https://github.com/django-import-export/django-import-export/issues/1515>`_.

How to create relation during import if it does not exist
---------------------------------------------------------

See :ref:`advanced_usage:Creating non existent relations`.

How to handle large file uploads
---------------------------------

If uploading large files, you may encounter time-outs.
See :ref:`Celery:Using celery to perform imports` and :ref:`bulk_import:Bulk imports`.


How to use field other than `id` in Foreign Key lookup
------------------------------------------------------

See :ref:`advanced_usage:Foreign key relations`.

``RelatedObjectDoesNotExist`` exception during import
-----------------------------------------------------

This can occur if a model defines a ``__str__()`` method which references a primary key or
foreign key relation, and which is ``None`` during import.  There is a workaround to deal
with this issue.  Refer to `this comment <https://github.com/django-import-export/django-import-export/issues/1556#issuecomment-1466980421>`_.

'failed to assign change_list_template attribute' warning in logs
-----------------------------------------------------------------

This indicates that the change_list_template attribute could not be set, most likely due to a clash with a third party
library.  Refer to :ref:`interoperability`.

``FileNotFoundError`` during Admin import 'confirm' step
--------------------------------------------------------

You may receive an error during import such as::

  FileNotFoundError [Errno 2] No such file or directory: '/tmp/tmp5abcdef'

This usually happens because you are running the Admin site in a multi server or container environment.
During import, the import file has to be stored temporarily and then retrieved for storage after confirmation.
Therefore ``FileNotFoundError`` error can occur because the temp storage is not available to the server process after
confirmation.

To resolve this, you should avoid using temporary file system storage in multi server environments.

Refer to :ref:`import process<import-process>` for more information.
