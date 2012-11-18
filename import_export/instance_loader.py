class BaseInstanceLoader(object):

    def __init__(self, importer):
        self.importer = importer

    def get_instance(self, row):
        raise NotImplementedError


class ModelInstanceLoader(BaseInstanceLoader):

    def get_instance(self, row):
        try:
            key = self.importer.get_mapping()[self.importer.import_code]
            return self.importer.model.objects.get(**{
                key: row[self.importer.import_code]
                })
        except self.importer.model.DoesNotExist:
            return None


class CachedInstanceLoader(BaseInstanceLoader):
    """
    Loads all model instances in memory to avoid hitting database on every
    ``get_instance`` call.
    """

    def cache_instances(self):
        key = self.importer.get_mapping()[self.importer.import_code]
        self.all_instances = dict([(getattr(instance, key), instance)
                for instance in self.importer.model.objects.all()])

    def get_instance(self, row):
        if not hasattr(self, 'all_instances'):
            self.cache_instances()
        return self.all_instances.get(row[self.importer.import_code])
