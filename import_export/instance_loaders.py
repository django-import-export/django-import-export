class BaseInstanceLoader(object):

    def __init__(self, resource, dataset=None):
        self.resource = resource
        self.dataset = dataset

    def get_instance(self, row):
        raise NotImplementedError


class ModelInstanceLoader(BaseInstanceLoader):

    def get_queryset(self):
        return self.resource._meta.model.objects.all()

    def get_instance(self, row):
        try:
            params = {}
            for key in self.resource.get_import_id_fields():
                field = self.resource.fields[key]
                params[field.attribute] = field.clean(row)
            return self.get_queryset().get(**params)
        except self.resource._meta.model.DoesNotExist:
            return None


class CachedInstanceLoader(ModelInstanceLoader):
    """
    Loads all model instances in memory to avoid hitting database on every
    ``get_instance`` call.
    """

    def __init__(self, *args, **kwargs):
        super(CachedInstanceLoader, self).__init__(*args, **kwargs)

        pk_field_name = self.resource.get_import_id_fields()[0]
        self.pk_field = self.resource.fields[pk_field_name]

        ids = [self.pk_field.clean(row) for row in self.dataset.dict]
        qs = self.get_queryset().filter(**{
            "%s__in" % self.pk_field.attribute: ids
            })

        self.all_instances = dict([
            (self.pk_field.get_value(instance), instance)
            for instance in qs])

    def get_instance(self, row):
        return self.all_instances.get(self.pk_field.clean(row))
