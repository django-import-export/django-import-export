Django Management Commands
==========================

Export Command
--------------

The ``export`` command allows you to export data from a specified Django model
or a resource class. The exported data can be saved in different formats, such
as CSV or XLSX.

Usage
-----

.. code-block:: bash

    python manage.py export <format> <resource> [--encoding ENCODING]

- **format**: Specify the format in which the data should be exported. -
- **resource**: Specify the resource or model to export. Accepts a resource class or a model class in dotted path format. - **--encoding** (optional): Specify the encoding (e.g., 'utf-8') to be used for the exported data.

Example
-------

.. code-block:: bash

    python manage.py export CSV auth.User

This command will export the User model data in CSV format using utf-8
encoding.

Another example:

.. code-block:: bash

    python manage.py export XLSX mymodule.resources.MyResource

This command will export the data from ``MyResource`` resource in XLSX format.

Import Command
--------------

The ``import`` command allows you to import data from a file using a specified
Django model or a custom resource class.

Usage
-----

.. code-block:: bash

    python manage.py import <resource> <import_file_name> [--format FORMAT] [--encoding ENCODING] [--dry-run] [--raise-errors]

- **resource**: The resource class or model class in dotted path format.
- **import_file_name**: The file from which data is imported (``-`` can be used to indicate stdin).
- **--format** (optional): Specify the format of the data to import. If not provided, it will be guessed from the mimetype.
- **--encoding** (optional): Specify the character encoding of the data.
- **--dry-run**: Perform a trial run without making changes.
- **--raise-errors**: Raise any encountered errors during execution.

Example
-------

Import data from file into auth.User model using default model resource:

.. code-block:: bash

    python manage.py import auth.User users.csv

Import data from file using custom model resource, raising errors:

.. code-block:: bash

    python manage.py import --raise-errors helper.MyUserResource users.csv

