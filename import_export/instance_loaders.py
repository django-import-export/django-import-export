class BaseInstanceLoader:
    """
    Base abstract implementation of instance loader.
    """

    def __init__(self, resource, dataset=None):
        self.resource = resource
        self.dataset = dataset

    def get_instance(self, row):
        raise NotImplementedError


class ModelInstanceLoader(BaseInstanceLoader):
    """
    Instance loader for Django model.

    Lookup for model instance by ``import_id_fields``.
    """

    def get_queryset(self):
        return self.resource.get_queryset()

    def get_instance(self, row):
        try:
            params = {}
            for key in self.resource.get_import_id_fields():
                field = self.resource.fields[key]
                params[field.attribute] = field.clean(row)
            if params:
                return self.get_queryset().get(**params)
            else:
                return None
        except self.resource._meta.model.DoesNotExist:
            return None


class CachedInstanceLoader(ModelInstanceLoader):
    """
    Loads all possible model instances in dataset avoid hitting database for
    every ``get_instance`` call.

    This instance loader work only when there is one ``import_id_fields``
    field.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        pk_field_name = self.resource.get_import_id_fields()[0]
        self.pk_field = self.resource.fields[pk_field_name]

        # If the pk field is missing, all instances in dataset are new
        # and cache is empty.
        self.all_instances = {}
        # Import ids that match more than one instance. These are tracked so
        # that get_instance() can raise MultipleObjectsReturned instead of
        # silently returning one of them, consistent with ModelInstanceLoader.
        self._duplicate_ids = set()
        if self.dataset.dict and self.pk_field.column_name in self.dataset.dict[0]:
            ids = [self.pk_field.clean(row) for row in self.dataset.dict]
            qs = self.get_queryset().filter(**{"%s__in" % self.pk_field.attribute: ids})

            for instance in qs:
                key = self.pk_field.get_value(instance)
                if key in self.all_instances:
                    self._duplicate_ids.add(key)
                self.all_instances[key] = instance

    def get_instance(self, row):
        if self.all_instances:
            key = self.pk_field.clean(row)
            if key in self._duplicate_ids:
                model = self.resource._meta.model
                raise model.MultipleObjectsReturned(
                    "get() returned more than one %s -- the import id "
                    "matches multiple objects." % model.__name__
                )
            return self.all_instances.get(key)
        return None
