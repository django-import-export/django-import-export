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

Further discussion `here <https://github.com/django-import-export/django-import-export/issues/1078/>`_ and `here <https://stackoverflow.com/a/71625152/39296/>`_.


.. _dynamically_set_resource_values:

How to dynamically set resource values
--------------------------------------

There are a few use cases where it is desirable to dynamically set values in Resources.  For example, suppose you are importing via the Admin console and want to use a value associated with the authenticated user in import queries.  This is easy to do.

Suppose the authenticated user (stored in the ``request`` object) has a property called ``organisation_id``.  During import, we want to filter any books associated only with that organisation.

First of all, override the import kwargs method so that the request user is retained::

    class BookAdmin(ImportExportMixin, admin.ModelAdmin):
        # attribute declarations not shown

        def get_import_resource_kwargs(self, request, *args, **kwargs):
            kwargs = super().get_resource_kwargs(request, *args, **kwargs)
            kwargs.update({"user": request.user})
            return kwargs

Now you can add a constructor to your ``Resource`` to store the user reference, then override ``get_queryset()`` to return books for the organisation::

    class BookResource(ModelResource):

        def __init__(self, user):
            self.user = user

        def get_queryset(self):
            return self._meta.model.objects.filter(organisation_id=self.user.organisation_id)

        class Meta:
            model = Book

Using this method, you can also dynamically set properties of the ``Field`` instance itself, including passing dynamic values to Widgets::

    class YourResource(ModelResource):

      def __init__(self, company_name):
          super().__init__()
          self.fields["custom_field"] = fields.Field(
              attribute="custom_field", column_name=company_name,
              widget=MyCompanyWidget(company_name)
          )

How to set a value on all imported instances prior to persisting
----------------------------------------------------------------

TODO this may belong in import data workflow rst

If you need to set the same value on each instance created during import then you can do so as follows.

It might be that you want to set an object read using a user id on each instance to be persisted

You can define your resource to take the associated instance as a param, and then set it on each import instance::

    class YourResource(ModelResource):

        def __init__(self, company):
            self.company = company

        def before_save_instance(self, instance, using_transactions, dry_run):
            instance.company = self.company

        class Meta:
            model = YourModel

See `this example <#how-to-dynamically-set-resource-values>`_ to see how to dynamically read request values.

How to export from more than one table
--------------------------------------

- https://stackoverflow.com/questions/74020864/is-it-possible-to-use-import-export-django-lib-to-export-data-from-more-than-one/74029584#74029584

- https://github.com/django-import-export/django-import-export/issues/1440

How to import imagefield in excel cell
--------------------------------------

- https://stackoverflow.com/questions/74093994/django-import-export-imagefield-in-excel-cell

- https://github.com/django-import-export/django-import-export/issues/90#issuecomment-729731655
- https://github.com/django-import-export/django-import-export/issues/90#issuecomment-1336181454

How to hide stack trace in UI error messages
--------------------------------------------

- https://github.com/django-import-export/django-import-export/issues/1257#issuecomment-952276485

Ids incremented twice during import
-----------------------------------

https://github.com/django-import-export/django-import-export/issues/560

https://wiki.postgresql.org/wiki/FAQ#Why_are_there_gaps_in_the_numbering_of_my_sequence.2FSERIAL_column.3F_Why_aren.27t_my_sequence_numbers_reused_on_transaction_abort.3F

how to handle blank Charfield
-----------------------------

https://stackoverflow.com/questions/61987773/django-import-export-how-to-handle-blank-charfield

https://github.com/django-import-export/django-import-export/issues/1485#issuecomment-1295859788

Foreign key is null when importing
----------------------------------

https://github.com/django-import-export/django-import-export/issues/1461

How to customize export data
----------------------------

https://stackoverflow.com/a/55046474/39296
https://stackoverflow.com/questions/74802453/export-only-the-data-registered-by-the-user-django-import-export

How to set export file encoding
-------------------------------

https://github.com/django-import-export/django-import-export/pull/1515

How to create relation during import if it does not exist
---------------------------------------------------------

https://stackoverflow.com/questions/74562802/import-into-tables-from-django-import-export

How to handle large file uploads
---------------------------------

https://github.com/django-import-export/django-import-export/issues/1524
