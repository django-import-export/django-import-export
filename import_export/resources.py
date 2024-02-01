import functools
import logging
import traceback
import warnings
from collections import OrderedDict
from copy import deepcopy

import tablib
from diff_match_patch import diff_match_patch
from django.conf import settings
from django.core.exceptions import (
    FieldDoesNotExist,
    ImproperlyConfigured,
    ValidationError,
)
from django.core.management.color import no_style
from django.core.paginator import Paginator
from django.db import connections, router
from django.db.models.fields.related import ForeignObjectRel
from django.db.models.query import QuerySet
from django.db.transaction import TransactionManagementError, set_rollback
from django.utils.encoding import force_str
from django.utils.safestring import mark_safe

from . import widgets
from .fields import Field
from .instance_loaders import ModelInstanceLoader
from .results import Error, Result, RowResult
from .utils import atomic_if_using_transaction

logger = logging.getLogger(__name__)
# Set default logging handler to avoid "No handler found" warnings.
logger.addHandler(logging.NullHandler())


def get_related_model(field):
    if hasattr(field, "related_model"):
        return field.related_model


def has_natural_foreign_key(model):
    """
    Determine if a model has natural foreign key functions
    """
    return hasattr(model, "natural_key") and hasattr(
        model.objects, "get_by_natural_key"
    )


class ResourceOptions:
    """
    The inner Meta class allows for class-level configuration of how the
    Resource should behave. The following options are available:
    """

    model = None
    """
    Django Model class. It is used to introspect available
    fields.

    """
    fields = None
    """
    Controls what introspected fields the Resource should include. A whitelist
    of fields.
    """

    exclude = None
    """
    Controls what introspected fields the Resource should
    NOT include. A blacklist of fields.
    """

    instance_loader_class = None
    """
    Controls which class instance will take
    care of loading existing objects.
    """

    import_id_fields = ["id"]
    """
    Controls which object fields will be used to
    identify existing instances.
    """

    export_order = None
    """
    Controls export order for columns.
    """

    widgets = None
    """
    This dictionary defines widget kwargs for fields.
    """

    use_transactions = None
    """
    Controls if import should use database transactions. Default value is
    ``None`` meaning ``settings.IMPORT_EXPORT_USE_TRANSACTIONS`` will be
    evaluated.
    """

    skip_unchanged = False
    """
    Controls if the import should skip unchanged records. Default value is
    False
    """

    report_skipped = True
    """
    Controls if the result reports skipped rows. Default value is True
    """

    clean_model_instances = False
    """
    Controls whether ``instance.full_clean()`` is called during the import
    process to identify potential validation errors for each (non skipped) row.
    The default value is False.
    """

    chunk_size = None
    """
    Controls the chunk_size argument of Queryset.iterator or,
    if prefetch_related is used, the per_page attribute of Paginator.
    """

    skip_diff = False
    """
    Controls whether or not an instance should be diffed following import.
    By default, an instance is copied prior to insert, update or delete.
    After each row is processed, the instance's copy is diffed against the original,
    and the value stored in each :class:`~import_export.results.RowResult`.
    If diffing is not required, then disabling the diff operation by setting this value
    to ``True`` improves performance, because the copy and comparison operations are
    skipped for each row.
    If enabled, then ``skip_row()`` checks do not execute, because 'skip' logic requires
    comparison between the stored and imported versions of a row.
    If enabled, then HTML row reports are also not generated (see ``skip_html_diff``).
    The default value is False.
    """

    skip_html_diff = False
    """
    Controls whether or not a HTML report is generated after each row.
    By default, the difference between a stored copy and an imported instance
    is generated in HTML form and stored in each
    :class:`~import_export.results.RowResult`.
    The HTML report is used to present changes on the confirmation screen in the admin
    site, hence when this value is ``True``, then changes will not be presented on the
    confirmation screen.
    If the HTML report is not required, then setting this value to ``True`` improves
    performance, because the HTML generation is skipped for each row.
    This is a useful optimization when importing large datasets.
    The default value is False.
    """

    use_bulk = False
    """
    Controls whether import operations should be performed in bulk.
    By default, an object's save() method is called for each row in a data set.
    When bulk is enabled, objects are saved using bulk operations.
    """

    batch_size = 1000
    """
    The batch_size parameter controls how many objects are created in a single query.
    The default is to create objects in batches of 1000.
    See `bulk_create()
    <https://docs.djangoproject.com/en/dev/ref/models/querysets/#bulk-create>`_.
    This parameter is only used if ``use_bulk`` is True.
    """

    force_init_instance = False
    """
    If True, this parameter will prevent imports from checking the database for existing
    instances.
    Enabling this parameter is a performance enhancement if your import dataset is
    guaranteed to contain new instances.
    """

    using_db = None
    """
    DB Connection name to use for db transactions. If not provided,
    ``router.db_for_write(model)`` will be evaluated and if it's missing,
    DEFAULT_DB_ALIAS constant ("default") is used.
    """

    store_row_values = False
    """
    If True, each row's raw data will be stored in each
    :class:`~import_export.results.RowResult`.
    Enabling this parameter will increase the memory usage during import
    which should be considered when importing large datasets.
    """

    store_instance = False
    """
    If True, the row instance will be stored in each
    :class:`~import_export.results.RowResult`.
    Enabling this parameter will increase the memory usage during import
    which should be considered when importing large datasets.
    """

    use_natural_foreign_keys = False
    """
    If True, use_natural_foreign_keys = True will be passed to all foreign
    key widget fields whose models support natural foreign keys. That is,
    the model has a natural_key function and the manager has a
    get_by_natural_key function.
    """


class DeclarativeMetaclass(type):
    def __new__(cls, name, bases, attrs):
        declared_fields = []
        meta = ResourceOptions()

        # If this class is subclassing another Resource, add that Resource's
        # fields. Note that we loop over the bases in *reverse*. This is
        # necessary in order to preserve the correct order of fields.
        for base in bases[::-1]:
            if hasattr(base, "fields"):
                declared_fields = list(base.fields.items()) + declared_fields
                # Collect the Meta options
                options = getattr(base, "Meta", None)
                for option in [
                    option
                    for option in dir(options)
                    if not option.startswith("_") and hasattr(options, option)
                ]:
                    setattr(meta, option, getattr(options, option))

        # Add direct fields
        for field_name, obj in attrs.copy().items():
            if isinstance(obj, Field):
                field = attrs.pop(field_name)
                if not field.column_name:
                    field.column_name = field_name
                declared_fields.append((field_name, field))

        attrs["fields"] = OrderedDict(declared_fields)
        new_class = super().__new__(cls, name, bases, attrs)

        # Add direct options
        options = getattr(new_class, "Meta", None)
        for option in [
            option
            for option in dir(options)
            if not option.startswith("_") and hasattr(options, option)
        ]:
            setattr(meta, option, getattr(options, option))
        new_class._meta = meta

        return new_class


class Diff:
    def __init__(self, resource, instance, new):
        self.left = self._export_resource_fields(resource, instance)
        self.right = []
        self.new = new

    def compare_with(self, resource, instance, dry_run=False):
        self.right = self._export_resource_fields(resource, instance)

    def as_html(self):
        data = []
        dmp = diff_match_patch()
        for v1, v2 in zip(self.left, self.right):
            if v1 != v2 and self.new:
                v1 = ""
            diff = dmp.diff_main(force_str(v1), force_str(v2))
            dmp.diff_cleanupSemantic(diff)
            html = dmp.diff_prettyHtml(diff)
            html = mark_safe(html)
            data.append(html)
        return data

    def _export_resource_fields(self, resource, instance):
        return [
            resource.export_field(f, instance) if instance else ""
            for f in resource.get_user_visible_fields()
        ]


class Resource(metaclass=DeclarativeMetaclass):
    """
    Resource defines how objects are mapped to their import and export
    representations and handle importing and exporting data.
    """

    def __init__(self, **kwargs):
        """
        kwargs:
           An optional dict of kwargs.
           Subclasses can use kwargs to pass dynamic values to enhance import / exports.
        """
        # The fields class attribute is the *class-wide* definition of
        # fields. Because a particular *instance* of the class might want to
        # alter self.fields, we create self.fields here by copying cls.fields.
        # Instances should always modify self.fields; they should not modify
        # cls.fields.
        self.fields = deepcopy(self.fields)

        # lists to hold model instances in memory when bulk operations are enabled
        self.create_instances = list()
        self.update_instances = list()
        self.delete_instances = list()

    @classmethod
    def get_result_class(self):
        """
        Returns the class used to store the result of an import.
        """
        return Result

    @classmethod
    def get_row_result_class(self):
        """
        Returns the class used to store the result of a row import.
        """
        return RowResult

    @classmethod
    def get_error_result_class(self):
        """
        Returns the class used to store an error resulting from an import.
        """
        return Error

    @classmethod
    def get_diff_class(self):
        """
        Returns the class used to display the diff for an imported instance.
        """
        return Diff

    @classmethod
    def get_db_connection_name(self):
        if self._meta.using_db is None:
            return router.db_for_write(self._meta.model)
        else:
            return self._meta.using_db

    def get_use_transactions(self):
        if self._meta.use_transactions is None:
            return getattr(settings, "IMPORT_EXPORT_USE_TRANSACTIONS", True)
        else:
            return self._meta.use_transactions

    def get_chunk_size(self):
        if self._meta.chunk_size is None:
            return getattr(settings, "IMPORT_EXPORT_CHUNK_SIZE", 100)
        else:
            return self._meta.chunk_size

    def get_fields(self, **kwargs):
        """
        Returns fields sorted according to
        :attr:`~import_export.resources.ResourceOptions.export_order`.
        """
        return [self.fields[f] for f in self.get_export_order()]

    def get_field_name(self, field):
        """
        Returns the field name for a given field.
        """
        for field_name, f in self.fields.items():
            if f == field:
                return field_name
        raise AttributeError(
            "Field %s does not exists in %s resource" % (field, self.__class__)
        )

    def init_instance(self, row=None):
        """
        Initializes an object. Implemented in
        :meth:`import_export.resources.ModelResource.init_instance`.
        """
        raise NotImplementedError()

    def get_instance(self, instance_loader, row):
        """
        If all 'import_id_fields' are present in the dataset, calls
        the :doc:`InstanceLoader <api_instance_loaders>`. Otherwise,
        returns `None`.
        """
        import_id_fields = [self.fields[f] for f in self.get_import_id_fields()]
        for field in import_id_fields:
            if field.column_name not in row:
                return
        return instance_loader.get_instance(row)

    def get_or_init_instance(self, instance_loader, row):
        """
        Either fetches an already existing instance or initializes a new one.
        """
        if not self._meta.force_init_instance:
            instance = self.get_instance(instance_loader, row)
            if instance:
                return (instance, False)
        return (self.init_instance(row), True)

    def get_import_id_fields(self):
        """ """
        return self._meta.import_id_fields

    def get_bulk_update_fields(self):
        """
        Returns the fields to be included in calls to bulk_update().
        ``import_id_fields`` are removed because `id` fields cannot be supplied to
        bulk_update().
        """
        return [f for f in self.fields if f not in self._meta.import_id_fields]

    def bulk_create(
        self, using_transactions, dry_run, raise_errors, batch_size=None, result=None
    ):
        """
        Creates objects by calling ``bulk_create``.
        """
        try:
            if len(self.create_instances) > 0:
                if not using_transactions and dry_run:
                    pass
                else:
                    self._meta.model.objects.bulk_create(
                        self.create_instances, batch_size=batch_size
                    )
        except Exception as e:
            self.handle_import_error(result, e, raise_errors)
        finally:
            self.create_instances.clear()

    def bulk_update(
        self, using_transactions, dry_run, raise_errors, batch_size=None, result=None
    ):
        """
        Updates objects by calling ``bulk_update``.
        """
        try:
            if len(self.update_instances) > 0:
                if not using_transactions and dry_run:
                    pass
                else:
                    self._meta.model.objects.bulk_update(
                        self.update_instances,
                        self.get_bulk_update_fields(),
                        batch_size=batch_size,
                    )
        except Exception as e:
            self.handle_import_error(result, e, raise_errors)
        finally:
            self.update_instances.clear()

    def bulk_delete(self, using_transactions, dry_run, raise_errors, result=None):
        """
        Deletes objects by filtering on a list of instances to be deleted,
        then calling ``delete()`` on the entire queryset.
        """
        try:
            if len(self.delete_instances) > 0:
                if not using_transactions and dry_run:
                    pass
                else:
                    delete_ids = [o.pk for o in self.delete_instances]
                    self._meta.model.objects.filter(pk__in=delete_ids).delete()
        except Exception as e:
            self.handle_import_error(result, e, raise_errors)
        finally:
            self.delete_instances.clear()

    def validate_instance(
        self, instance, import_validation_errors=None, validate_unique=True
    ):
        """
        Takes any validation errors that were raised by
        :meth:`~import_export.resources.Resource.import_obj`, and combines them
        with validation errors raised by the instance's ``full_clean()``
        method. The combined errors are then re-raised as single, multi-field
        ValidationError.

        If the ``clean_model_instances`` option is False, the instances's
        ``full_clean()`` method is not called, and only the errors raised by
        ``import_obj()`` are re-raised.
        """
        if import_validation_errors is None:
            errors = {}
        else:
            errors = import_validation_errors.copy()
        if self._meta.clean_model_instances:
            try:
                instance.full_clean(
                    exclude=errors.keys(),
                    validate_unique=validate_unique,
                )
            except ValidationError as e:
                errors = e.update_error_dict(errors)

        if errors:
            raise ValidationError(errors)

    def save_instance(
        self, instance, is_create, using_transactions=True, dry_run=False
    ):
        """
        Takes care of saving the object to the database.

        Objects can be created in bulk if ``use_bulk`` is enabled.

        :param instance: The instance of the object to be persisted.
        :param is_create: A boolean flag to indicate whether this is a new object
                          to be created, or an existing object to be updated.
        :param using_transactions: A flag to indicate whether db transactions are used.
        :param dry_run: A flag to indicate dry-run mode.
        """
        self.before_save_instance(instance, using_transactions, dry_run)
        if self._meta.use_bulk:
            if is_create:
                self.create_instances.append(instance)
            else:
                self.update_instances.append(instance)
        else:
            if not using_transactions and dry_run:
                # we don't have transactions and we want to do a dry_run
                pass
            else:
                instance.save()
        self.after_save_instance(instance, using_transactions, dry_run)

    def before_save_instance(self, instance, using_transactions, dry_run):
        """
        Override to add additional logic. Does nothing by default.
        """
        pass

    def after_save_instance(self, instance, using_transactions, dry_run):
        """
        Override to add additional logic. Does nothing by default.
        """
        pass

    def delete_instance(self, instance, using_transactions=True, dry_run=False):
        """
        Calls :meth:`instance.delete` as long as ``dry_run`` is not set.
        If ``use_bulk`` then instances are appended to a list for bulk import.
        """
        self.before_delete_instance(instance, dry_run)
        if self._meta.use_bulk:
            self.delete_instances.append(instance)
        else:
            if not using_transactions and dry_run:
                # we don't have transactions and we want to do a dry_run
                pass
            else:
                instance.delete()
        self.after_delete_instance(instance, dry_run)

    def before_delete_instance(self, instance, dry_run):
        """
        Override to add additional logic. Does nothing by default.
        """
        pass

    def after_delete_instance(self, instance, dry_run):
        """
        Override to add additional logic. Does nothing by default.
        """
        pass

    def import_field(self, field, obj, data, is_m2m=False, **kwargs):
        """
        Calls :meth:`import_export.fields.Field.save` if ``Field.attribute``
        is specified, and ``Field.column_name`` is found in ``data``.
        """
        if field.attribute and field.column_name in data:
            field.save(obj, data, is_m2m, **kwargs)

    def get_import_fields(self):
        return self.get_fields()

    def import_obj(self, obj, data, dry_run, **kwargs):
        """
        Traverses every field in this Resource and calls
        :meth:`~import_export.resources.Resource.import_field`. If
        ``import_field()`` results in a ``ValueError`` being raised for
        one of more fields, those errors are captured and reraised as a single,
        multi-field ValidationError."""
        errors = {}
        for field in self.get_import_fields():
            if isinstance(field.widget, widgets.ManyToManyWidget):
                continue
            try:
                self.import_field(field, obj, data, **kwargs)
            except ValueError as e:
                errors[field.attribute] = ValidationError(force_str(e), code="invalid")
        if errors:
            raise ValidationError(errors)

    def save_m2m(self, obj, data, using_transactions, dry_run):
        """
        Saves m2m fields.

        Model instance need to have a primary key value before
        a many-to-many relationship can be used.
        """
        if (not using_transactions and dry_run) or self._meta.use_bulk:
            # we don't have transactions and we want to do a dry_run
            # OR use_bulk is enabled (m2m operations are not supported
            # for bulk operations)
            pass
        else:
            for field in self.get_import_fields():
                if not isinstance(field.widget, widgets.ManyToManyWidget):
                    continue
                self.import_field(field, obj, data, True)

    def for_delete(self, row, instance):
        """
        Returns ``True`` if ``row`` importing should delete instance.

        Default implementation returns ``False``.
        Override this method to handle deletion.
        """
        return False

    def skip_row(self, instance, original, row, import_validation_errors=None):
        """
        Returns ``True`` if ``row`` importing should be skipped.

        Default implementation returns ``False`` unless skip_unchanged == True
        and skip_diff == False.

        If skip_diff is True, then no comparisons can be made because ``original``
        will be None.

        When left unspecified, skip_diff and skip_unchanged both default to ``False``,
        and rows are never skipped.

        By default, rows are not skipped if validation errors have been detected
        during import.  You can change this behavior and choose to ignore validation
        errors by overriding this method.

        Override this method to handle skipping rows meeting certain
        conditions.

        Use ``super`` if you want to preserve default handling while overriding
        ::

            class YourResource(ModelResource):
                def skip_row(self, instance, original,
                             row, import_validation_errors=None):
                    # Add code here
                    return super().skip_row(instance, original, row,
                                            import_validation_errors=import_validation_errors)
        """
        if (
            not self._meta.skip_unchanged
            or self._meta.skip_diff
            or import_validation_errors
        ):
            return False
        for field in self.get_import_fields():
            # For fields that are models.fields.related.ManyRelatedManager
            # we need to compare the results
            if isinstance(field.widget, widgets.ManyToManyWidget):
                # #1437 - handle m2m field not present in import file
                if field.column_name not in row.keys():
                    continue
                # m2m instance values are taken from the 'row' because they
                # have not been written to the 'instance' at this point
                instance_values = list(field.clean(row))
                original_values = (
                    list()
                    if original.pk is None
                    else list(field.get_value(original).all())
                )
                if len(instance_values) != len(original_values):
                    return False

                if sorted(v.pk for v in instance_values) != sorted(
                    v.pk for v in original_values
                ):
                    return False
            else:
                if field.get_value(instance) != field.get_value(original):
                    return False
        return True

    def get_diff_headers(self):
        """
        Diff representation headers.
        """
        return self.get_user_visible_headers()

    def before_import(self, dataset, using_transactions, dry_run, **kwargs):
        """
        Override to add additional logic. Does nothing by default.
        """
        pass

    def after_import(self, dataset, result, using_transactions, dry_run, **kwargs):
        """
        Override to add additional logic. Does nothing by default.
        """
        pass

    def before_import_row(self, row, row_number=None, **kwargs):
        """
        Override to add additional logic. Does nothing by default.
        """
        pass

    def after_import_row(self, row, row_result, row_number=None, **kwargs):
        """
        Override to add additional logic. Does nothing by default.

        :param row: A ``dict`` of the import row.

        :param row_result: A ``RowResult`` instance.
          References the persisted ``instance`` as an attribute.

        :param row_number: The row number from the dataset.
        """
        pass

    def after_import_instance(self, instance, new, row_number=None, **kwargs):
        """
        Override to add additional logic. Does nothing by default.
        """
        pass

    def handle_import_error(self, result, error, raise_errors=False):
        logger.debug(error, exc_info=error)
        if result:
            tb_info = traceback.format_exc()
            result.append_base_error(self.get_error_result_class()(error, tb_info))
        if raise_errors:
            raise

    def import_row(
        self,
        row,
        instance_loader,
        using_transactions=True,
        dry_run=False,
        raise_errors=None,
        **kwargs
    ):
        """
        Imports data from ``tablib.Dataset``. Refer to :doc:`import_workflow`
        for a more complete description of the whole import process.

        :param row: A ``dict`` of the row to import

        :param instance_loader: The instance loader to be used to load the row

        :param using_transactions: If ``using_transactions`` is set, a transaction
            is being used to wrap the import

        :param dry_run: If ``dry_run`` is set, or error occurs, transaction
            will be rolled back.
        """
        if raise_errors is not None:
            warnings.warn(
                "raise_errors argument is deprecated and "
                "will be removed in a future release.",
                category=DeprecationWarning,
            )

        skip_diff = self._meta.skip_diff
        row_result = self.get_row_result_class()()
        if self._meta.store_row_values:
            row_result.row_values = row
        original = None
        try:
            self.before_import_row(row, **kwargs)
            instance, new = self.get_or_init_instance(instance_loader, row)
            self.after_import_instance(instance, new, **kwargs)
            if new:
                row_result.import_type = RowResult.IMPORT_TYPE_NEW
            else:
                row_result.import_type = RowResult.IMPORT_TYPE_UPDATE
            row_result.new_record = new
            if not skip_diff:
                original = deepcopy(instance)
                diff = self.get_diff_class()(self, original, new)
            if self.for_delete(row, instance):
                if new:
                    row_result.import_type = RowResult.IMPORT_TYPE_SKIP
                    if not skip_diff:
                        diff.compare_with(self, None, dry_run)
                else:
                    row_result.import_type = RowResult.IMPORT_TYPE_DELETE
                    row_result.add_instance_info(instance)
                    if self._meta.store_instance:
                        row_result.instance = instance
                    self.delete_instance(instance, using_transactions, dry_run)
                    if not skip_diff:
                        diff.compare_with(self, None, dry_run)
            else:
                import_validation_errors = {}
                try:
                    self.import_obj(instance, row, dry_run, **kwargs)
                except ValidationError as e:
                    # Validation errors from import_obj() are passed on to
                    # validate_instance(), where they can be combined with model
                    # instance validation errors if necessary
                    import_validation_errors = e.update_error_dict(
                        import_validation_errors
                    )

                if self.skip_row(instance, original, row, import_validation_errors):
                    row_result.import_type = RowResult.IMPORT_TYPE_SKIP
                else:
                    self.validate_instance(instance, import_validation_errors)
                    self.save_instance(instance, new, using_transactions, dry_run)
                    self.save_m2m(instance, row, using_transactions, dry_run)
                row_result.add_instance_info(instance)
                if self._meta.store_instance:
                    row_result.instance = instance
                if not skip_diff:
                    diff.compare_with(self, instance, dry_run)
                    if not new:
                        row_result.original = original

            if not skip_diff and not self._meta.skip_html_diff:
                row_result.diff = diff.as_html()
            self.after_import_row(row, row_result, **kwargs)

        except ValidationError as e:
            row_result.import_type = RowResult.IMPORT_TYPE_INVALID
            row_result.validation_error = e
        except Exception as e:
            row_result.import_type = RowResult.IMPORT_TYPE_ERROR
            # There is no point logging a transaction error for each row
            # when only the original error is likely to be relevant
            if not isinstance(e, TransactionManagementError):
                logger.debug(e, exc_info=e)
            tb_info = traceback.format_exc()
            row_result.errors.append(self.get_error_result_class()(e, tb_info, row))

        return row_result

    def import_data(
        self,
        dataset,
        dry_run=False,
        raise_errors=False,
        use_transactions=None,
        collect_failed_rows=False,
        rollback_on_validation_errors=False,
        **kwargs
    ):
        """
        Imports data from ``tablib.Dataset``. Refer to :doc:`import_workflow`
        for a more complete description of the whole import process.

        :param dataset: A ``tablib.Dataset``

        :param raise_errors: Whether errors should be printed to the end user
                             or raised regularly.

        :param use_transactions: If ``True`` the import process will be processed
                                 inside a transaction.

        :param collect_failed_rows: If ``True`` the import process will collect
                                    failed rows.

        :param rollback_on_validation_errors: If both ``use_transactions`` and
                                              ``rollback_on_validation_errors``
                                              are set to ``True``, the import
                                              process will be rolled back in
                                              case of ValidationError.

        :param dry_run: If ``dry_run`` is set, or an error occurs, if a transaction
                        is being used, it will be rolled back.
        """

        if use_transactions is None:
            use_transactions = self.get_use_transactions()

        db_connection = self.get_db_connection_name()
        connection = connections[db_connection]
        supports_transactions = getattr(
            connection.features, "supports_transactions", False
        )

        if use_transactions and not supports_transactions:
            raise ImproperlyConfigured

        using_transactions = (use_transactions or dry_run) and supports_transactions

        if self._meta.batch_size is not None and (
            not isinstance(self._meta.batch_size, int) or self._meta.batch_size < 0
        ):
            raise ValueError("Batch size must be a positive integer")

        with atomic_if_using_transaction(using_transactions, using=db_connection):
            result = self.import_data_inner(
                dataset,
                dry_run,
                raise_errors,
                using_transactions,
                collect_failed_rows,
                **kwargs
            )
            if using_transactions and (
                dry_run
                or result.has_errors()
                or (rollback_on_validation_errors and result.has_validation_errors())
            ):
                set_rollback(True, using=db_connection)
            return result

    def import_data_inner(
        self,
        dataset,
        dry_run,
        raise_errors,
        using_transactions,
        collect_failed_rows,
        rollback_on_validation_errors=None,
        **kwargs
    ):
        if rollback_on_validation_errors is not None:
            warnings.warn(
                "rollback_on_validation_errors argument is deprecated and will be "
                "removed in a future release.",
                category=DeprecationWarning,
            )

        result = self.get_result_class()()
        result.diff_headers = self.get_diff_headers()
        result.total_rows = len(dataset)
        db_connection = self.get_db_connection_name()

        try:
            with atomic_if_using_transaction(using_transactions, using=db_connection):
                self.before_import(dataset, using_transactions, dry_run, **kwargs)
        except Exception as e:
            self.handle_import_error(result, e, raise_errors)

        instance_loader = self._meta.instance_loader_class(self, dataset)

        # Update the total in case the dataset was altered by before_import()
        result.total_rows = len(dataset)

        if collect_failed_rows:
            result.add_dataset_headers(dataset.headers)

        for i, data_row in enumerate(dataset, 1):
            row = OrderedDict(zip(dataset.headers, data_row))
            with atomic_if_using_transaction(
                using_transactions and not self._meta.use_bulk, using=db_connection
            ):
                row_result = self.import_row(
                    row,
                    instance_loader,
                    using_transactions=using_transactions,
                    dry_run=dry_run,
                    row_number=i,
                    **kwargs
                )
            if self._meta.use_bulk:
                # persist a batch of rows
                # because this is a batch, any exceptions are logged and not associated
                # with a specific row
                if len(self.create_instances) == self._meta.batch_size:
                    with atomic_if_using_transaction(
                        using_transactions, using=db_connection
                    ):
                        self.bulk_create(
                            using_transactions,
                            dry_run,
                            raise_errors,
                            batch_size=self._meta.batch_size,
                            result=result,
                        )
                if len(self.update_instances) == self._meta.batch_size:
                    with atomic_if_using_transaction(
                        using_transactions, using=db_connection
                    ):
                        self.bulk_update(
                            using_transactions,
                            dry_run,
                            raise_errors,
                            batch_size=self._meta.batch_size,
                            result=result,
                        )
                if len(self.delete_instances) == self._meta.batch_size:
                    with atomic_if_using_transaction(
                        using_transactions, using=db_connection
                    ):
                        self.bulk_delete(
                            using_transactions, dry_run, raise_errors, result=result
                        )

            result.increment_row_result_total(row_result)

            if row_result.errors:
                if collect_failed_rows:
                    result.append_failed_row(row, row_result.errors[0])
                if raise_errors:
                    raise row_result.errors[-1].error
            elif row_result.validation_error:
                result.append_invalid_row(i, row, row_result.validation_error)
                if collect_failed_rows:
                    result.append_failed_row(row, row_result.validation_error)
                if raise_errors:
                    raise row_result.validation_error
            if (
                row_result.import_type != RowResult.IMPORT_TYPE_SKIP
                or self._meta.report_skipped
            ):
                result.append_row_result(row_result)

        if self._meta.use_bulk:
            # bulk persist any instances which are still pending
            with atomic_if_using_transaction(using_transactions, using=db_connection):
                self.bulk_create(
                    using_transactions, dry_run, raise_errors, result=result
                )
                self.bulk_update(
                    using_transactions, dry_run, raise_errors, result=result
                )
                self.bulk_delete(
                    using_transactions, dry_run, raise_errors, result=result
                )

        try:
            with atomic_if_using_transaction(using_transactions, using=db_connection):
                self.after_import(
                    dataset, result, using_transactions, dry_run, **kwargs
                )
        except Exception as e:
            self.handle_import_error(result, e, raise_errors)

        return result

    def get_export_order(self):
        order = tuple(self._meta.export_order or ())
        return order + tuple(k for k in self.fields if k not in order)

    def before_export(self, queryset, *args, **kwargs):
        """
        Override to add additional logic. Does nothing by default.
        """
        pass

    def after_export(self, queryset, data, *args, **kwargs):
        """
        Override to add additional logic. Does nothing by default.
        """
        pass

    def filter_export(self, queryset, *args, **kwargs):
        """
        Override to filter an export queryset.
        """
        return queryset

    def export_field(self, field, obj):
        field_name = self.get_field_name(field)
        dehydrate_method = field.get_dehydrate_method(field_name)

        method = getattr(self, dehydrate_method, None)
        if method is not None:
            return method(obj)
        return field.export(obj)

    def get_export_fields(self):
        return self.get_fields()

    def export_resource(self, obj):
        return [self.export_field(field, obj) for field in self.get_export_fields()]

    def get_export_headers(self):
        headers = [force_str(field.column_name) for field in self.get_export_fields()]
        return headers

    def get_user_visible_headers(self):
        headers = [
            force_str(field.column_name) for field in self.get_user_visible_fields()
        ]
        return headers

    def get_user_visible_fields(self):
        return self.get_fields()

    def iter_queryset(self, queryset):
        if not isinstance(queryset, QuerySet):
            yield from queryset
        elif queryset._prefetch_related_lookups:
            # Django's queryset.iterator ignores prefetch_related which might result
            # in an excessive amount of db calls. Therefore we use pagination
            # as a work-around
            if not queryset.query.order_by:
                # Paginator() throws a warning if there is no sorting
                # attached to the queryset
                queryset = queryset.order_by("pk")
            paginator = Paginator(queryset, self.get_chunk_size())
            for index in range(paginator.num_pages):
                yield from paginator.get_page(index + 1)
        else:
            yield from queryset.iterator(chunk_size=self.get_chunk_size())

    def export(self, *args, queryset=None, **kwargs):
        """
        Exports a resource.
        :returns: Dataset object.
        """
        if len(args) == 1 and (
            isinstance(args[0], QuerySet) or isinstance(args[0], list)
        ):
            # issue 1565: definition of export() was incorrect
            # if queryset is being passed, it must be as the first arg or named
            # parameter
            # this logic is included for backwards compatibility:
            # if the method is being called without a named parameter, add a warning
            # this check should be removed in a future release
            warnings.warn(
                "'queryset' must be supplied as a named parameter",
                category=DeprecationWarning,
            )
            queryset = args[0]

        self.before_export(queryset, *args, **kwargs)

        if queryset is None:
            queryset = self.get_queryset()
        queryset = self.filter_export(queryset, *args, **kwargs)
        headers = self.get_export_headers()
        data = tablib.Dataset(headers=headers)

        for obj in self.iter_queryset(queryset):
            data.append(self.export_resource(obj))

        self.after_export(queryset, data, *args, **kwargs)

        return data


class ModelDeclarativeMetaclass(DeclarativeMetaclass):
    def __new__(cls, name, bases, attrs):
        new_class = super().__new__(cls, name, bases, attrs)

        opts = new_class._meta

        if not opts.instance_loader_class:
            opts.instance_loader_class = ModelInstanceLoader

        if opts.model:
            model_opts = opts.model._meta
            declared_fields = new_class.fields

            field_list = []
            for f in sorted(model_opts.fields + model_opts.many_to_many):
                if opts.fields is not None and f.name not in opts.fields:
                    continue
                if opts.exclude and f.name in opts.exclude:
                    continue
                if f.name in declared_fields:
                    continue

                field = new_class.field_from_django_field(f.name, f, readonly=False)
                field_list.append(
                    (
                        f.name,
                        field,
                    )
                )

            new_class.fields.update(OrderedDict(field_list))

            # add fields that follow relationships
            if opts.fields is not None:
                field_list = []
                for field_name in opts.fields:
                    if field_name in declared_fields:
                        continue
                    if field_name.find("__") == -1:
                        continue

                    model = opts.model
                    attrs = field_name.split("__")
                    for i, attr in enumerate(attrs):
                        verbose_path = ".".join(
                            [opts.model.__name__] + attrs[0 : i + 1]
                        )

                        try:
                            f = model._meta.get_field(attr)
                        except FieldDoesNotExist as e:
                            logger.debug(e, exc_info=e)
                            raise FieldDoesNotExist(
                                "%s: %s has no field named '%s'"
                                % (verbose_path, model.__name__, attr)
                            )

                        if i < len(attrs) - 1:
                            # We're not at the last attribute yet, so check
                            # that we're looking at a relation, and move on to
                            # the next model.
                            if isinstance(f, ForeignObjectRel):
                                model = get_related_model(f)
                            else:
                                if get_related_model(f) is None:
                                    raise KeyError(
                                        "%s is not a relation" % verbose_path
                                    )
                                model = get_related_model(f)

                    if isinstance(f, ForeignObjectRel):
                        f = f.field

                    field = new_class.field_from_django_field(
                        field_name, f, readonly=True
                    )
                    field_list.append((field_name, field))

                new_class.fields.update(OrderedDict(field_list))

        return new_class


class ModelResource(Resource, metaclass=ModelDeclarativeMetaclass):
    """
    ModelResource is Resource subclass for handling Django models.
    """

    DEFAULT_RESOURCE_FIELD = Field

    WIDGETS_MAP = {
        "ManyToManyField": "get_m2m_widget",
        "OneToOneField": "get_fk_widget",
        "ForeignKey": "get_fk_widget",
        "CharField": widgets.CharWidget,
        "DecimalField": widgets.DecimalWidget,
        "DateTimeField": widgets.DateTimeWidget,
        "DateField": widgets.DateWidget,
        "TimeField": widgets.TimeWidget,
        "DurationField": widgets.DurationWidget,
        "FloatField": widgets.FloatWidget,
        "IntegerField": widgets.IntegerWidget,
        "PositiveIntegerField": widgets.IntegerWidget,
        "BigIntegerField": widgets.IntegerWidget,
        "PositiveSmallIntegerField": widgets.IntegerWidget,
        "SmallIntegerField": widgets.IntegerWidget,
        "SmallAutoField": widgets.IntegerWidget,
        "AutoField": widgets.IntegerWidget,
        "BigAutoField": widgets.IntegerWidget,
        "NullBooleanField": widgets.BooleanWidget,
        "BooleanField": widgets.BooleanWidget,
        "JSONField": widgets.JSONWidget,
    }

    @classmethod
    def get_m2m_widget(cls, field):
        """
        Prepare widget for m2m field
        """
        return functools.partial(
            widgets.ManyToManyWidget, model=get_related_model(field)
        )

    @classmethod
    def get_fk_widget(cls, field):
        """
        Prepare widget for fk and o2o fields
        """

        model = get_related_model(field)

        use_natural_foreign_keys = (
            has_natural_foreign_key(model) and cls._meta.use_natural_foreign_keys
        )

        return functools.partial(
            widgets.ForeignKeyWidget,
            model=model,
            use_natural_foreign_keys=use_natural_foreign_keys,
        )

    @classmethod
    def widget_from_django_field(cls, f, default=widgets.Widget):
        """
        Returns the widget that would likely be associated with each
        Django type.

        Includes mapping of Postgres Array field. In the case that
        psycopg2 is not installed, we consume the error and process the field
        regardless.
        """
        result = default
        internal_type = ""
        if callable(getattr(f, "get_internal_type", None)):
            internal_type = f.get_internal_type()

        if internal_type in cls.WIDGETS_MAP:
            result = cls.WIDGETS_MAP[internal_type]
            if isinstance(result, str):
                result = getattr(cls, result)(f)
        else:
            try:
                from django.contrib.postgres.fields import ArrayField
            except ImportError:
                # ImportError: No module named psycopg2.extras
                class ArrayField:
                    pass

            if isinstance(f, ArrayField):
                return widgets.SimpleArrayWidget

        return result

    @classmethod
    def widget_kwargs_for_field(self, field_name):
        """
        Returns widget kwargs for given field_name.
        """
        if self._meta.widgets:
            return self._meta.widgets.get(field_name, {})
        return {}

    @classmethod
    def field_from_django_field(cls, field_name, django_field, readonly):
        """
        Returns a Resource Field instance for the given Django model field.
        """

        FieldWidget = cls.widget_from_django_field(django_field)
        widget_kwargs = cls.widget_kwargs_for_field(field_name)
        field = cls.DEFAULT_RESOURCE_FIELD(
            attribute=field_name,
            column_name=field_name,
            widget=FieldWidget(**widget_kwargs),
            readonly=readonly,
            default=django_field.default,
        )
        return field

    def get_queryset(self):
        """
        Returns a queryset of all objects for this model. Override this if you
        want to limit the returned queryset.
        """
        return self._meta.model.objects.all()

    def init_instance(self, row=None):
        """
        Initializes a new Django model.
        """
        return self._meta.model()

    def after_import(self, dataset, result, using_transactions, dry_run, **kwargs):
        """
        Reset the SQL sequences after new objects are imported
        """
        # Adapted from django's loaddata
        if not dry_run and any(
            r.import_type == RowResult.IMPORT_TYPE_NEW for r in result.rows
        ):
            db_connection = self.get_db_connection_name()
            connection = connections[db_connection]
            sequence_sql = connection.ops.sequence_reset_sql(
                no_style(), [self._meta.model]
            )
            if sequence_sql:
                cursor = connection.cursor()
                try:
                    for line in sequence_sql:
                        cursor.execute(line)
                finally:
                    cursor.close()

    @classmethod
    def get_display_name(cls):
        if hasattr(cls._meta, "name"):
            return cls._meta.name
        return cls.__name__


def modelresource_factory(model, resource_class=ModelResource):
    """
    Factory for creating ``ModelResource`` class for given Django model.
    """
    attrs = {"model": model}
    Meta = type(str("Meta"), (object,), attrs)

    class_name = model.__name__ + str("Resource")

    class_attrs = {
        "Meta": Meta,
    }

    metaclass = ModelDeclarativeMetaclass
    return metaclass(class_name, (resource_class,), class_attrs)
