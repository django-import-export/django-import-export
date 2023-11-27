from django.test import TestCase

from import_export import fields
from import_export.resources import Resource

from .resources import MyResource


class TestInheritance(TestCase):
    # Issue 140 Attributes aren't inherited by subclasses
    def test_inheritance(self):
        class A(MyResource):
            inherited = fields.Field()

            class Meta:
                import_id_fields = ("email",)

        class B(A):
            local = fields.Field()

            class Meta:
                export_order = ("email", "extra")

        resource = B()
        self.assertIn("name", resource.fields)
        self.assertIn("inherited", resource.fields)
        self.assertIn("local", resource.fields)
        self.assertEqual(
            resource.get_export_headers(),
            ["email", "extra", "name", "inherited", "local"],
        )
        self.assertEqual(resource._meta.import_id_fields, ("email",))

    def test_inheritance_with_custom_attributes(self):
        class A(MyResource):
            inherited = fields.Field()

            class Meta:
                import_id_fields = ("email",)
                custom_attribute = True

        class B(A):
            local = fields.Field()

        resource = B()
        self.assertEqual(resource._meta.custom_attribute, True)


class TestMultiInheritance(TestCase):
    def test_meta_inheritance_3_levels(self):
        # issue 1363
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

    def test_meta_inheritance_2_levels(self):
        class GrandparentResource(Resource):
            class Meta:
                batch_size = 666

        class ParentResource(GrandparentResource):
            class Meta:
                batch_size = 333

        class ChildResource(ParentResource):
            class Meta:
                pass

        parent_resource = ParentResource()
        child_resource = ChildResource()
        self.assertEqual(333, parent_resource._meta.batch_size)
        self.assertEqual(333, child_resource._meta.batch_size)

    def test_meta_inheritance_1_level(self):
        class GrandparentResource(Resource):
            class Meta:
                batch_size = 666

        class ParentResource(GrandparentResource):
            class Meta:
                batch_size = 333

        class ChildResource(ParentResource):
            class Meta:
                batch_size = 111

        parent_resource = ParentResource()
        child_resource = ChildResource()
        self.assertEqual(333, parent_resource._meta.batch_size)
        self.assertEqual(111, child_resource._meta.batch_size)

    def test_meta_inheritance_default(self):
        class GrandparentResource(Resource):
            class Meta:
                pass

        class ParentResource(GrandparentResource):
            class Meta:
                pass

        class ChildResource(ParentResource):
            class Meta:
                pass

        grandparent_resource = GrandparentResource()
        parent_resource = ParentResource()
        child_resource = ChildResource()
        self.assertEqual(1000, grandparent_resource._meta.batch_size)
        self.assertEqual(1000, parent_resource._meta.batch_size)
        self.assertEqual(1000, child_resource._meta.batch_size)
