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

    Note: When there is more than one field in `import_id_fields`, may load
    instances not present in dataset (loads cartesian product of all values
    in dataset across all `import_id_fields`), so the cache memory usage may
    be unexpectedly large.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.all_instances = {}
        self.pk_fields = [self.resource.fields[key] for key in self.resource.get_import_id_fields()]
        # If the pk fields are missing, all instances in dataset are new
        # and cache is empty.
        if self.dataset.dict and all(field.column_name in self.dataset.dict[0] for field in self.pk_fields):
            ids = [{field.clean(row) for row in self.dataset.dict} for field in self.pk_fields]
            qs = self.get_queryset().filter(**{
                "%s__in" % field.attribute: ids[i] for i, field in enumerate(self.pk_fields)
                })

            self.all_instances = {
                tuple(field.get_value(instance) for field in self.pk_fields): instance
                for instance in qs
            }

    def get_instance(self, row):
        if self.all_instances:
            return self.all_instances.get(tuple(field.clean(row) for field in self.pk_fields))
        return None
