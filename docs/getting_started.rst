===============
Getting started
===============

For example purposes, we'll be use simplified book app, here is our
``core.models.py``::

    class Author(models.Model):
        name = models.CharField(max_length=100)

        def __unicode__(self):
            return self.name


    class Category(models.Model):
        name = models.CharField(max_length=100)

        def __unicode__(self):
            return self.name


    class Book(models.Model):
        name = models.CharField('Book name', max_length=100)
        author = models.ForeignKey(Author, blank=True, null=True)
        author_email = models.EmailField('Author email', max_length=75, blank=True)
        imported = models.BooleanField(default=False)
        published = models.DateField('Published', blank=True, null=True)
        price = models.DecimalField(max_digits=10, decimal_places=2, null=True,
                blank=True)
        categories = models.ManyToManyField(Category, blank=True)

        def __unicode__(self):
            return self.name


.. _base-modelresource:

Creating import-export resource
-------------------------------

To integrate `django-import-export` with ``Book`` model, we will create
resource class that will describe  how this resource can be imported or
exported.

::

    from import_export import resources
    from core.models import Book


    class BookResource(resources.ModelResource):

        class Meta:
            model = Book

Exporting data
--------------

Now that we have defined resource class, we can export books::

    >>> dataset = BookResource().export()
    >>> print dataset.csv
    id,name,author,author_email,imported,published,price,categories
    2,Some book,1,,0,2012-12-05,8.85,1

Customize resource options
--------------------------

By default ``ModelResource`` introspects model fields and creates
``import_export.fields.Field`` attribute with appopriate widget for each
field.

To affect which model fields will be included in import-export resource,
use ``fields`` option to whitelist fields or ``exclude`` option for
to blacklist fields::

    class BookResource(resources.ModelResource):

        class Meta:
            model = Book
            exclude = ('imported', )

When defining ``ModelResource`` fields it is possible to follow
model relationships::

    class BookResource(resources.ModelResource):

        class Meta:
            model = Book
            fields = ('author__name',)

.. note::

    Following relationship fields sets ``field`` as readonly, meaning
    this field will be skipped when importing data.

.. seealso::

    :doc:`/api_resources`
        

Declaring fields
----------------

It is possible to override resource fields to change some of it's
options::

    from import_export import fields

    class BookResource(resources.ModelResource):
        published = fields.Field(column_name='published_date')
        
        class Meta:
            model = Book

Other fields, that are not existing in target model may be added::

    from import_export import fields
    
    class BookResource(resources.ModelResource):
        myfield = fields.Field(column_name='myfield')

        class Meta:
            model = Book

.. seealso::

    :doc:`/api_fields`
        Available field types and options.


Advanced data manipulation
--------------------------

Not all data can be easily pull off an object/model attribute.
In order to turn complicated data model into a (generally simpler) processed
data structure, ``dehydrate_<fieldname>`` method should be defined::

    from import_export import fields

    class BookResource(resources.ModelResource):
        full_title = fields.Field()
        
        class Meta:
            model = Book

        def dehydrate_full_title(self, book):
            return '%s by %s' % (book.name, book.name.author)


Customize widgets
-----------------

``ModelResource`` creates field with default widget for given field type.
If widget should be initialized with different arguments, set ``widgets``
dict.

In this example widget for ``published`` field is overriden to
use different date format. This format will be used both for importing
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

Importing data
--------------

Let's import data::

    >>> import tablib
    >>> from import_export import resources
    >>> from core.models import Book
    >>> book_resource = resources.modelresource_factory(model=Book)()
    >>> dataset = tablib.Dataset(['', 'New book'], headers=['id', 'name'])
    >>> result = book_resource.import_data(dataset, dry_run=True)
    >>> print result.has_errors()
    False
    >>> result = book_resource.import_data(dataset, dry_run=False)

In 4th line we use ``modelresource_factory`` to create default
``ModelResource``. ModelResource class created this way is equal
as in :ref:`base-modelresource`.

In 5th line ``Dataset`` with subset of ``Book`` fields is created.

In rest of code we first pretend to import data with ``dry_run`` set, then
check for any errors and import data.

.. seealso::

    :doc:`/import_workflow`
        for detailed import workflow descripton and customization options.

Admin integration
-----------------

Admin integration is achived by subclassing 
``ImportExportModelAdmin`` or one of mixins::

    from import_export.admin import ImportExportModelAdmin


    class BookAdmin(ImportExportModelAdmin):
        pass

.. seealso::

    :doc:`/api_admin`
        available mixins and options.
