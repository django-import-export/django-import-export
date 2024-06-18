===============
Getting started
===============

Introduction
============

This section describes how to get started with import-export.  We'll use the :ref:`example application<exampleapp>`
as a guide.

import-export can be used programmatically as described here, or it can be integrated with the
:ref:`Django Admin interface<admin-integration>`.

Test data
=========

There are sample files which can be used to test importing data in the `tests/core/exports` directory.

The test models
===============

For example purposes, we'll use a simplified book app. Here is our
``models.py``::

    # app/models.py

    class Author(models.Model):
        name = models.CharField(max_length=100)

        def __str__(self):
            return self.name


    class Category(models.Model):
        name = models.CharField(max_length=100)

        def __str__(self):
            return self.name


    class Book(models.Model):
        name = models.CharField('Book name', max_length=100)
        author = models.ForeignKey(Author, blank=True, null=True)
        author_email = models.EmailField('Author email', max_length=75, blank=True)
        imported = models.BooleanField(default=False)
        published = models.DateField('Published', blank=True, null=True)
        price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
        categories = models.ManyToManyField(Category, blank=True)

        def __str__(self):
            return self.name


.. _base-modelresource:

Creating a resource
===============================

To integrate import-export with our ``Book`` model, we will create a
:class:`~import_export.resources.ModelResource` class in ``admin.py`` that will
describe how this resource can be imported or exported::

    # app/admin.py

    from import_export import resources
    from core.models import Book

    class BookResource(resources.ModelResource):

        class Meta:
            model = Book  # or 'core.Book'

Importing data
==============

Let's import some data!

.. code-block:: python
    :linenos:
    :emphasize-lines: 4,5

    >>> import tablib
    >>> from import_export import resources
    >>> from core.models import Book
    >>> book_resource = resources.modelresource_factory(model=Book)()
    >>> dataset = tablib.Dataset(['', 'New book'], headers=['id', 'name'])
    >>> result = book_resource.import_data(dataset, dry_run=True)
    >>> print(result.has_errors())
    False
    >>> result = book_resource.import_data(dataset, dry_run=False)

In the fourth line we use :func:`~import_export.resources.modelresource_factory`
to create a default :class:`~import_export.resources.ModelResource`.
The ``ModelResource`` class created this way is equal to the one shown in the
example in section :ref:`base-modelresource`.

In fifth line a :class:`~tablib.Dataset` with columns ``id`` and ``name``, and
one book entry, are created. A field (or combination of fields) which uniquely identifies an instance always needs to
be present.  This is so that the import process can manage creates / updates.  In this case, we use ``id``.
For more information, see :ref:`advanced_usage:Create or update model instances`.

In the rest of the code we first pretend to import data using
:meth:`~import_export.resources.Resource.import_data` and ``dry_run`` set,
then check for any errors and actually import data this time.

.. seealso::

    :doc:`/import_workflow`
        for a detailed description of the import workflow and its customization options.

Deleting data
-------------

To delete objects during import, implement the
:meth:`~import_export.resources.Resource.for_delete` method on
your :class:`~import_export.resources.Resource` class.
You should add custom logic which will signify which rows are to be deleted.

For example, suppose you would like to have a field in the import dataset to indicate which rows should be deleted.
You could include a field called *delete* which has either a 1 or 0 value.

In this case, declare the resource as follows::

    class BookResource(resources.ModelResource):

        def for_delete(self, row, instance):
            return row["delete"] == "1"

        class Meta:
            model = Book

If the delete flag is set on a *'new'* instance (i.e. the row does not already exist in the db) then the row will be
skipped.

.. _exporting_data:

Exporting data
==============

Now that we have defined a :class:`~import_export.resources.ModelResource` class,
we can export books::

    >>> from core.admin import BookResource
    >>> dataset = BookResource().export()
    >>> print(dataset.csv)
    id,name,author,author_email,imported,published,price,categories
    2,Some book,1,,0,2012-12-05,8.85,1

.. warning::

    Data exported programmatically is not sanitized for malicious content.
    You will need to understand the implications of this and handle accordingly.
    See :ref:`admin_security`.
