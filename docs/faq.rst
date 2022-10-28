==========================
Frequently Asked Questions
==========================

What's the best way to communicate a problem, question, or suggestion?
======================================================================

To submit a feature, to report a bug, or to ask a question, please refer our :doc:`contributing guidelines <contributing>`.

How can I help?
===============

We welcome contributions from the community.

You can help in the following ways:

* Reporting bugs or issues.

* Answering questions which arise on Stack Overflow or as Github issues.

* Providing translations for UI text.

* Suggesting features or changes.

We encourage you to read the :doc:`contributing guidelines <contributing>`.

Common issues
=============

key error 'id' in ``get_import_id_fields()``
--------------------------------------------

When attempting to import, this error can be seen.  This indicates that the ``Resource`` has not been configured correctly, and the import logic fails.  A more detailed discussion is provided `here <https://stackoverflow.com/a/69347073/39296/>`_.

How to handle double-save from Signals
--------------------------------------

This issue can apply if you have implemented post-save signals, and you are using the import workflow in the Admin interface.  You will find that the post-save signal is called twice for each instance.  The reason for this is that the model ``save()`` method is called twice: once for the 'confirm' step and once for the 'import' step.  The call to ``save()`` during the 'confirm' step is necessary to prove that the object will be saved successfully, or to report any exceptions in the Admin UI if save failed.  After the 'confirm' step, the database transaction is rolled back so that no changes are persisted.

Therefore there is no way at present to stop ``save()`` being called twice, and there will always be two signal calls.  There is a workaround, which is to set a temporary flag on the instance being saved::

    class BookResource(resources.ModelResource):

        def before_save_instance(self, instance, using_transactions, dry_run):
            # during 'confirm' step, dry_run is True
            instance.dry_run = dry_run

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

Further discussion `here <https://github.com/django-import-export/django-import-export/issues/1078/>`_ and `here <https://stackoverflow.com/a/71625152/39296/>`_

How to dynamically set column name
----------------------------------

https://github.com/django-import-export/django-import-export/issues/1489

How to export from more than one table
--------------------------------------

- https://stackoverflow.com/questions/74020864/is-it-possible-to-use-import-export-django-lib-to-export-data-from-more-than-one/74029584#74029584

- https://github.com/django-import-export/django-import-export/issues/1440

How to import imagefield in excel cell
--------------------------------------

- https://stackoverflow.com/questions/74093994/django-import-export-imagefield-in-excel-cell

- https://github.com/django-import-export/django-import-export/issues/90#issuecomment-729731655

How to hide stack trace in UI error messages
--------------------------------------------

- https://github.com/django-import-export/django-import-export/issues/1257#issuecomment-952276485

Ids incremented twice during import
-----------------------------------

https://github.com/django-import-export/django-import-export/issues/560

https://wiki.postgresql.org/wiki/FAQ#Why_are_there_gaps_in_the_numbering_of_my_sequence.2FSERIAL_column.3F_Why_aren.27t_my_sequence_numbers_reused_on_transaction_abort.3F
