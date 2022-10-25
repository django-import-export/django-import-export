===============
Getting started
===============

Test data
=========

There are test data files which can be used for importing in the `test/core/exports` directory.

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

Creating import-export resource
===============================

To integrate `django-import-export` with our ``Book`` model, we will create a
:class:`~import_export.resources.ModelResource` class in ``admin.py`` that will
describe how this resource can be imported or exported::

    # app/admin.py

    from import_export import resources
    from core.models import Book

    class BookResource(resources.ModelResource):

        class Meta:
            model = Book

Exporting data
==============

Now that we have defined a :class:`~import_export.resources.ModelResource` class,
we can export books::

    >>> from app.admin import BookResource
    >>> dataset = BookResource().export()
    >>> print(dataset.csv)
    id,name,author,author_email,imported,published,price,categories
    2,Some book,1,,0,2012-12-05,8.85,1

Customize resource options
==========================

By default :class:`~import_export.resources.ModelResource` introspects model
fields and creates :class:`~import_export.fields.Field`-attributes with an
appropriate :class:`~import_export.widgets.Widget` for each field.

To affect which model fields will be included in an import-export
resource, use the ``fields`` option to whitelist fields::

    class BookResource(resources.ModelResource):

        class Meta:
            model = Book
            fields = ('id', 'name', 'price',)

Or the ``exclude`` option to blacklist fields::

    class BookResource(resources.ModelResource):

        class Meta:
            model = Book
            exclude = ('imported', )

An explicit order for exporting fields can be set using the ``export_order``
option::

    class BookResource(resources.ModelResource):

        class Meta:
            model = Book
            fields = ('id', 'name', 'author', 'price',)
            export_order = ('id', 'price', 'author', 'name')

The default field for object identification is ``id``, you can optionally set
which fields are used as the ``id`` when importing::

    class BookResource(resources.ModelResource):

        class Meta:
            model = Book
            import_id_fields = ('isbn',)
            fields = ('isbn', 'name', 'author', 'price',)

When defining :class:`~import_export.resources.ModelResource` fields it is
possible to follow model relationships::

    class BookResource(resources.ModelResource):

        class Meta:
            model = Book
            fields = ('author__name',)

.. note::

    Following relationship fields sets ``field`` as readonly, meaning
    this field will be skipped when importing data.

By default all records will be imported, even if no changes are detected. This
can be changed setting the ``skip_unchanged`` option. Also, the
``report_skipped`` option controls whether skipped records appear in the import
``Result`` object, and if using the admin whether skipped records will show in
the import preview page::

    class BookResource(resources.ModelResource):

        class Meta:
            model = Book
            skip_unchanged = True
            report_skipped = False
            fields = ('id', 'name', 'price',)

To further customize the resources, you might like to consider overriding the following
:class:`~import_export.admin.ImportMixin` methods:
:meth:`~import_export.admin.ImportMixin.get_resource_kwargs`,
:meth:`~import_export.admin.ImportMixin.get_resource_classes`,
:meth:`~import_export.admin.ImportMixin.get_export_resource_kwargs`,

.. seealso::

    :doc:`/api_resources`


Declaring fields
================

It is possible to override a resource field to change some of its
options::

    from import_export.fields import Field

    class BookResource(resources.ModelResource):
        published = Field(attribute='published', column_name='published_date')

        class Meta:
            model = Book

Other fields that don't exist in the target model may be added::

    from import_export.fields import Field

    class BookResource(resources.ModelResource):
        myfield = Field(column_name='myfield')

        class Meta:
            model = Book

.. seealso::

    :doc:`/api_fields`
        Available field types and options.


Advanced data manipulation on export
====================================

Not all data can be easily extracted from an object/model attribute.
In order to turn complicated data model into a (generally simpler) processed
data structure on export, ``dehydrate_<fieldname>`` method should be defined::

    from import_export.fields import Field

    class BookResource(resources.ModelResource):
        full_title = Field()

        class Meta:
            model = Book

        def dehydrate_full_title(self, book):
            book_name = getattr(book, "name", "unknown")
            author_name = getattr(book.author, "name", "unknown")
            return '%s by %s' % (book_name, author_name)

In this case, the export looks like this:

    >>> from app.admin import BookResource
    >>> dataset = BookResource().export()
    >>> print(dataset.csv)
    full_title,id,name,author,author_email,imported,published,price,categories
    Some book by 1,2,Some book,1,,0,2012-12-05,8.85,1


Customize widgets
=================

A :class:`~import_export.resources.ModelResource` creates a field with a
default widget for a given field type. If the widget should be initialized
with different arguments, set the ``widgets`` dict.

In this example widget, the ``published`` field is overridden to use a
different date format. This format will be used both for importing
and exporting resource.

::

    class BookResource(resources.ModelResource):

        class Meta:
            model = Book
            widgets = {
                    'published': {'format': '%d.%m.%Y'},
                    }

.. seealso::

    :doc:`/api_widgets`
        available widget types and options.

Django Natural Keys
===================

The ``ForeignKeyWidget`` also supports using Django's natural key functions. A
manager class with the ``get_by_natural_key`` function is required for importing
foreign key relationships by the field model's natural key, and the model must
have a ``natural_key`` function that can be serialized as a JSON list in order to
export data.

The primary utility for natural key functionality is to enable exporting data
that can be imported into other Django environments with different numerical
primary key sequences. The natural key functionality enables handling more
complex data than specifying either a single field or the PK.

The example below illustrates how to create a field on the ``BookResource`` that
imports and exports its author relationships using the natural key functions
on the ``Author`` model and modelmanager.

The resource _meta option ``use_natural_foreign_keys`` enables this setting
for all Models that support it.

::

    from import_export.fields import Field
    from import_export.widgets import ForeignKeyWidget

    class AuthorManager(models.Manager):

        def get_by_natural_key(self, name):
            return self.get(name=name)

    class Author(models.Model):

        objects = AuthorManager()

        name = models.CharField(max_length=100)
        birthday = models.DateTimeField(auto_now_add=True)

        def natural_key(self):
            return (self.name,)

    # Only the author field uses natural foreign keys.
    class BookResource(resources.ModelResource):

        author = Field(
            column_name = "author",
            attribute = "author",
            widget = ForeignKeyWidget(Author, use_natural_foreign_keys=True)
        )

        class Meta:
            model = Book

    # All widgets with foreign key functions use them.
    class BookResource(resources.ModelResource):

        class Meta:
            model = Book
            use_natural_foreign_keys = True

Read more at `Django Serialization <https://docs.djangoproject.com/en/4.0/topics/serialization>`_


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
The ModelResource class created this way is equal to the one shown in the
example in section :ref:`base-modelresource`.

In fifth line a :class:`~tablib.Dataset` with columns ``id`` and ``name``, and
one book entry, are created. A field for a primary key field (in this case,
``id``) always needs to be present.

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

The following is an example resource which expects a ``delete`` field in the
dataset. An import using this resource will delete model instances for rows
that have their column ``delete`` set to ``1``::

    class BookResource(resources.ModelResource):
        delete = fields.Field(widget=widgets.BooleanWidget())

        def for_delete(self, row, instance):
            return self.fields['delete'].clean(row)

        class Meta:
            model = Book


Signals
=======

To hook in the import export workflow, you can connect to ``post_import``,
``post_export`` signals::

    from django.dispatch import receiver
    from import_export.signals import post_import, post_export

    @receiver(post_import, dispatch_uid='balabala...')
    def _post_import(model, **kwargs):
        # model is the actual model instance which after import
        pass

    @receiver(post_export, dispatch_uid='balabala...')
    def _post_export(model, **kwargs):
        # model is the actual model instance which after export
        pass


.. _admin-integration:

Admin integration
=================

Exporting
---------

Exporting via list filters
~~~~~~~~~~~~~~~~~~~~~~~~~~

Admin integration is achieved by subclassing
:class:`~import_export.admin.ImportExportModelAdmin` or one of the available
mixins (:class:`~import_export.admin.ImportMixin`,
:class:`~import_export.admin.ExportMixin`,
:class:`~import_export.admin.ImportExportMixin`)::

    # app/admin.py
    from .models import Book
    from import_export.admin import ImportExportModelAdmin

    class BookAdmin(ImportExportModelAdmin):
        resource_classes = [BookResource]

    admin.site.register(Book, BookAdmin)

.. _change-screen-figure:

.. figure:: _static/images/django-import-export-change.png

   A screenshot of the change view with Import and Export buttons.

.. warning::

    The `resource_class` parameter was deprecated in `django-import-export` 3.0.
    Assign list or tuple with Resource(s) to `resource_classes` parameter now.


Exporting via admin action
~~~~~~~~~~~~~~~~~~~~~~~~~~

Another approach to exporting data is by subclassing
:class:`~import_export.admin.ImportExportActionModelAdmin` which implements
export as an admin action. As a result it's possible to export a list of
objects selected on the change list page::

    # app/admin.py
    from import_export.admin import ImportExportActionModelAdmin

    class BookAdmin(ImportExportActionModelAdmin):
        pass


.. figure:: _static/images/django-import-export-action.png

   A screenshot of the change view with Import and Export as an admin action.

Note that to use the :class:`~import_export.admin.ExportMixin` or
:class:`~import_export.admin.ExportActionMixin`, you must declare this mixin
**before** ``admin.ModelAdmin``::

    # app/admin.py
    from django.contrib import admin
    from import_export.admin import ExportActionMixin

    class BookAdmin(ExportActionMixin, admin.ModelAdmin):
        pass

Note that :class:`~import_export.admin.ExportActionMixin` is declared first in
the example above!


Importing
---------

It is also possible to enable data import via standard Django admin interface.
To do this subclass :class:`~import_export.admin.ImportExportModelAdmin` or use
one of the available mixins, i.e. :class:`~import_export.admin.ImportMixin`, or
:class:`~import_export.admin.ImportExportMixin`. Customizations are, of course,
possible.

.. _confirm-import-figure:

.. figure:: _static/images/django-import-export-import.png

   A screenshot of the import view.

.. figure:: _static/images/django-import-export-import-confirm.png

   A screenshot of the confirm import view.


Customize admin import forms
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

It is possible to modify default import forms used in the model admin. For
example, to add an additional field in the import form, subclass and extend the
:class:`~import_export.forms.ImportForm` (note that you may want to also
consider :class:`~import_export.forms.ConfirmImportForm` as importing is a
two-step process).

To use your customized form(s), change the respective attributes on your
``ModelAdmin`` class:

* :attr:`~import_export.admin.ImportMixin.import_form_class`
* :attr:`~import_export.admin.ImportMixin.confirm_form_class`

For example, imagine you want to import books for a specific author. You can
extend the import forms to include ``author`` field to select the author from.

Customize forms::

    from django import forms

    class CustomImportForm(ImportForm):
        author = forms.ModelChoiceField(
            queryset=Author.objects.all(),
            required=True)

    class CustomConfirmImportForm(ConfirmImportForm):
        author = forms.ModelChoiceField(
            queryset=Author.objects.all(),
            required=True)

Customize ``ModelAdmin``::

    class CustomBookAdmin(ImportMixin, admin.ModelAdmin):
        resource_classes = [BookResource]
        import_form_class = CustomImportForm
        confirm_form_class = CustomConfirmImportForm

        def get_confirm_form_initial(self, request, import_form):
            initial = super().get_confirm_form_initial(request, import_form)
            # Pass on the `author` value from the import form to
            # the confirm form (if provided)
            if import_form:
                initial['author'] = import_form.cleaned_data['author']
            return initial

    admin.site.register(Book, CustomBookAdmin)

To further customize the import forms, you might like to consider overriding the following
:class:`~import_export.admin.ImportMixin` methods:
:meth:`~import_export.admin.ImportMixin.get_import_form_class`,
:meth:`~import_export.admin.ImportMixin.get_import_form_kwargs`,
:meth:`~import_export.admin.ImportMixin.get_import_form_initial`,
:meth:`~import_export.admin.ImportMixin.get_confirm_form_class`,
:meth:`~import_export.admin.ImportMixin.get_confirm_form_kwargs`,

.. warning::

    The `resource_class` parameter was deprecated in `django-import-export` 3.0.
    Assign list or tuple with Resource(s) to `resource_classes` parameter now.


.. seealso::

    :doc:`/api_admin`
        available mixins and options.

Import confirmation
~~~~~~~~~~~~~~~~~~~

Importing in the Admin site is a two step process.

#. Choose the file to import (:ref:`screenshot<change-screen-figure>`).
#. Review changes and confirm import (:ref:`screenshot<confirm-import-figure>`).

To support this, uploaded data is written to temporary storage after step 1, and read
back for final import after step 2.

There are three mechanisms for temporary storage.

#. Temporary file storage on the host server (default).  This is suitable for development only.
   Use of temporary filesystem storage is not recommended for production sites.

#. The `Django cache <https://docs.djangoproject.com/en/dev/topics/cache/>`_.

#. `Django storage <https://docs.djangoproject.com/en/dev/ref/files/storage/>`_.

To modify which storage mechanism is used, please refer to the setting :ref:`IMPORT_EXPORT_TMP_STORAGE_CLASS`.

Temporary resources are removed when data is successfully imported after the confirmation step.

Your choice of temporary storage will be influenced by the following factors:

* Sensitivity of the data being imported.
* Volume and frequency of uploads.
* File upload size.
* Use of containers or load-balanced servers.

.. warning::

    If users do not complete the confirmation step of the workflow,
    or if there are errors during import, then temporary resources may not be deleted.
    This will need to be understood and managed in production settings.
    For example, using a cache expiration policy or cron job to clear stale resources.


Using multiple resources
------------------------

It is possible to set multiple resources both to import and export `ModelAdmin` classes.
The `ImportMixin`, `ExportMixin`, `ImportExportMixin` and `ImportExportModelAdmin` classes accepts
subscriptable type (list, tuple, ...) as `resource_classes` parameter.
The subscriptable could also be returned from one of the
`get_resource_classes()`, `get_import_resource_classes()`, `get_export_resource_classes()` classes.

If there are multiple resources, the resource chooser appears in import/export admin form.
The displayed name of the resource can be changed through the `name` parameter of the `Meta` class.


Use multiple resources::

    from import_export import resources
    from core.models import Book


    class BookResource(resources.ModelResource):

        class Meta:
            model = Book


    class BookNameResource(resources.ModelResource):

        class Meta:
            model = Book
            fields = ['id', 'name']
            name = "Export/Import only book names"


    class CustomBookAdmin(ImportMixin, admin.ModelAdmin):
        resource_classes = [BookResource, BookNameResource]
