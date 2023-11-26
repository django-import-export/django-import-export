from django.test import TestCase

from import_export.resources import Resource


class TestDeclarative(TestCase):
    def test_meta_inheritance(self):
        class GrandparentResource(Resource):
            class Meta:
                batch_size = 666

        class ParentResource(GrandparentResource):
            class Meta:
                pass

        class ChildResource(ParentResource):
            class Meta:
                pass

        parent_resource = ParentResource()
        child_resource = ChildResource()
        self.assertEqual(666, parent_resource._meta.batch_size)
        self.assertEqual(666, child_resource._meta.batch_size)
