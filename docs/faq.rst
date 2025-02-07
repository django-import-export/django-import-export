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

* Answering questions which arise on `Stack Overflow <https://stackoverflow.com/questions/tagged/django-import-export/>`_ or as Github issues.

* Providing translations for UI text.

* Suggesting features or changes.

We encourage you to read the :doc:`contributing guidelines <contributing>`.

.. _common_issues:

Common issues
=============

.. _import_id_fields_error_on_import:

``import_id_fields`` error on import
------------------------------------

The following error message can be seen on import:

  *The following fields are declared in 'import_id_fields' but are not present in the resource*

This indicates that the Resource has not been configured correctly, and the import logic fails.  Specifically,
the import process is attempting to use either the defined or default values for
:attr:`~import_export.options.ResourceOptions.import_id_fields` and no matching field has been detected in the resource
fields. See :ref:`advanced_usage:Create or update model instances`.

In cases where you are deliberately using generated fields in ``import_id_fields`` and these fields are not present in
the dataset, then you need to modify the resource definition to accommodate this.
See :ref:`dynamic_fields`.

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

Please refer to :ref:`format_ui_error_messages`.

Ids incremented twice during import
-----------------------------------

When importing using the Admin site, it can be that the ids of the imported instances are different from those show
in the preview step.  This occurs because the rows are imported during 'confirm', and then the transaction is rolled
back prior to the confirm step.  Database implementations mean that sequence numbers may not be reused.

Consider enabling :ref:`import_export_skip_admin_confirm` as a workaround.

See `this issue <https://github.com/django-import-export/django-import-export/issues/560>`_ for more detailed
discussion.

Not Null constraint fails when importing blank CharField
--------------------------------------------------------

This was an issue in v3 which is resolved in v4. The issue arises when importing from Excel because empty cells
are converted to ``None`` during import.  If the import process attempted to save a null value then a 'NOT NULL'
exception was raised.

In v4, initialization checks to see if the Django ``CharField`` has
`blank <https://docs.djangoproject.com/en/stable/ref/models/fields/#blank>`_ set to ``True``.
If it does, then null values or empty strings are persisted as empty strings.

If it is necessary to persist ``None`` instead of an empty string, then the ``allow_blank`` widget parameter can be
set::

    class BookResource(resources.ModelResource):

        name = Field(widget=CharWidget(allow_blank=False))

        class Meta:
            model = Book

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

See :ref:`creating-non-existent-relations`.

How to handle large file imports
--------------------------------

If uploading large files, you may encounter time-outs.
See :ref:`Using celery<celery>` and :ref:`bulk_import:Bulk imports`.

Performance issues or unexpected behavior during import
-------------------------------------------------------

This could be due to hidden rows in Excel files.
Hidden rows can be excluded using :ref:`import_export_import_ignore_blank_lines`.

Refer to `this PR <https://github.com/django-import-export/django-import-export/pull/2028>`_ for more information.


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

How to skip rows with validation errors during import
-----------------------------------------------------

Refer to `this comment <https://github.com/django-import-export/django-import-export/issues/763#issuecomment-1861031723>`_.

``FileNotFoundError`` during Admin import 'confirm' step
--------------------------------------------------------

You may receive an error during import such as::

  FileNotFoundError [Errno 2] No such file or directory: '/tmp/tmp5abcdef'

This usually happens because you are running the Admin site in a multi server or container environment.
During import, the import file has to be stored temporarily and then retrieved for storage after confirmation.
Therefore ``FileNotFoundError`` error can occur because the temp storage is not available to the server process after
confirmation.

To resolve this, you should avoid using temporary file system storage in multi server environments.

Refer to :ref:`import_confirmation` for more information.

How to export large datasets
----------------------------

Large datasets can be exported in a number of ways, depending on data size and preferences.

#. You can write custom scripts or `Admin commands <https://docs.djangoproject.com/en/stable/howto/custom-management-commands/>`_
   to handle the export.  Output can be written to a local filesystem, cloud bucket, network storage etc.
   Refer to the documentation on exporting :ref:`programmatically<exporting_data>`.
#. You can use the third party library :doc:`django-import-export-celery <celery>` to handle long-running exports.
#. You can enable :ref:`export via admin action<export_via_admin_action>` and then select items for export page by page
   in the Admin UI.  This will work if you have a relatively small number of pages and can handle export to multiple
   files.  This method is suitable as a one-off or as a simple way to export large datasets via the Admin UI.

How to change column names on export
------------------------------------

If you want to modify the names of the columns on export, you can do so by overriding
:meth:`~import_export.resources.Resource.get_export_headers`::

  class BookResource(ModelResource):

    def get_export_headers(self, fields=None):
      headers = super().get_export_headers(fields=fields)
      for i, h in enumerate(headers):
          if h == 'name':
            headers[i] = "NEW COLUMN NAME"
      return headers

    class Meta:
      model = Book

How to configure logging
------------------------

Refer to :ref:`logging configuration<logging>` for more information.

Export to Excel gives ``IllegalCharacterError``
-----------------------------------------------

This occurs when your data contains a character which cannot be rendered in Excel.
You can configure import-export to :ref:`sanitize these characters<import_export_escape_illegal_chars_on_export>`.
