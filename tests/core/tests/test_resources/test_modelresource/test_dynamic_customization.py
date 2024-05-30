import tablib
from core.models import (
    Book,
    Category,
    Entry,
    Profile,
    WithDynamicDefault,
    WithFloatField,
)
from core.tests.resources import BookResource, CategoryResource
from django.contrib.auth.models import User
from django.core.exceptions import FieldDoesNotExist
from django.db.models import Count
from django.db.utils import ConnectionDoesNotExist
from django.test import TestCase

from import_export import exceptions, fields, resources, results


class DynamicBehaviorCustomizationTest(TestCase):
    def setUp(self):
        self.resource = BookResource()
        self.book = Book.objects.create(name="Some book")
        self.dataset = tablib.Dataset(headers=["id", "name", "author_email", "price"])
        row = [self.book.pk, "Some book", "test@example.com", "10.25"]
        self.dataset.append(row)

    def test_related_one_to_one(self):
        # issue #17 - Exception when attempting access something on the
        # related_name

        user = User.objects.create(username="foo")
        profile = Profile.objects.create(user=user)
        Entry.objects.create(user=user)
        Entry.objects.create(user=User.objects.create(username="bar"))

        class EntryResource(resources.ModelResource):
            class Meta:
                model = Entry
                fields = ("user__profile", "user__profile__is_private")

        resource = EntryResource()
        dataset = resource.export(Entry.objects.all())
        self.assertEqual(dataset.dict[0]["user__profile"], profile.pk)
        self.assertEqual(dataset.dict[0]["user__profile__is_private"], "1")
        self.assertEqual(dataset.dict[1]["user__profile"], "")
        self.assertEqual(dataset.dict[1]["user__profile__is_private"], "")

    def test_empty_get_queryset(self):
        # issue #25 - Overriding queryset on export() fails when passed
        # queryset has zero elements
        dataset = self.resource.export(queryset=Book.objects.none())
        self.assertEqual(len(dataset), 0)

    def test_import_data_skip_unchanged(self):
        class MyBookResource(resources.ModelResource):
            save_count = 0

            def save_instance(self, instance, is_create, row, **kwargs):
                self.save_count += 1

            class Meta:
                skip_unchanged = True
                model = Book

        # Make sure we test with ManyToMany related objects
        cat1 = Category.objects.create(name="Cat 1")
        cat2 = Category.objects.create(name="Cat 2")
        self.book.categories.add(cat1)
        self.book.categories.add(cat2)
        dataset = self.resource.export()

        # Create a new resource that attempts to reimport the data currently
        # in the database while skipping unchanged rows (i.e. all of them)
        resource = MyBookResource()
        result = resource.import_data(dataset, raise_errors=True)
        self.assertFalse(result.has_errors())
        self.assertEqual(len(result.rows), len(dataset))
        self.assertTrue(result.rows[0].diff)
        self.assertEqual(result.rows[0].import_type, results.RowResult.IMPORT_TYPE_SKIP)
        self.assertEqual(result.rows[0].object_id, self.book.pk)
        if resource.save_count > 0:
            self.fail("Resource attempted to save instead of skipping")

        # Test that we can suppress reporting of skipped rows
        resource._meta.report_skipped = False
        result = resource.import_data(dataset, raise_errors=True)
        self.assertFalse(result.has_errors())
        self.assertEqual(len(result.rows), 0)

    def test_before_import_access_to_kwargs(self):
        class B(BookResource):
            def before_import(self, dataset, **kwargs):
                if "extra_arg" in kwargs:
                    dataset.headers[dataset.headers.index("author_email")] = "old_email"
                    dataset.insert_col(
                        0, lambda row: kwargs["extra_arg"], header="author_email"
                    )

        resource = B()
        result = resource.import_data(
            self.dataset, raise_errors=True, extra_arg="extra@example.com"
        )
        self.assertFalse(result.has_errors())
        self.assertEqual(len(result.rows), 1)
        instance = Book.objects.get(pk=self.book.pk)
        self.assertEqual(instance.author_email, "extra@example.com")

    def test_before_import_raises_error(self):
        class B(BookResource):
            def before_import(self, dataset, **kwargs):
                raise Exception("This is an invalid dataset")

        resource = B()
        with self.assertRaises(exceptions.ImportError) as cm:
            resource.import_data(self.dataset, raise_errors=True)
        self.assertEqual("This is an invalid dataset", cm.exception.error.args[0])

    def test_after_import_raises_error(self):
        class B(BookResource):
            def after_import(self, dataset, result, **kwargs):
                raise Exception("This is an invalid dataset")

        resource = B()
        with self.assertRaises(exceptions.ImportError) as cm:
            resource.import_data(self.dataset, raise_errors=True)
        self.assertEqual("This is an invalid dataset", cm.exception.error.args[0])

    def test_link_to_nonexistent_field(self):
        with self.assertRaises(FieldDoesNotExist) as cm:

            class BrokenBook1(resources.ModelResource):
                class Meta:
                    model = Book
                    fields = ("nonexistent__invalid",)

        self.assertEqual(
            "Book.nonexistent: Book has no field named 'nonexistent'",
            cm.exception.args[0],
        )

        with self.assertRaises(FieldDoesNotExist) as cm:

            class BrokenBook2(resources.ModelResource):
                class Meta:
                    model = Book
                    fields = ("author__nonexistent",)

        self.assertEqual(
            "Book.author.nonexistent: Author has no field named " "'nonexistent'",
            cm.exception.args[0],
        )

    def test_link_to_nonrelation_field(self):
        with self.assertRaises(KeyError) as cm:

            class BrokenBook1(resources.ModelResource):
                class Meta:
                    model = Book
                    fields = ("published__invalid",)

        self.assertEqual("Book.published is not a relation", cm.exception.args[0])

        with self.assertRaises(KeyError) as cm:

            class BrokenBook2(resources.ModelResource):
                class Meta:
                    model = Book
                    fields = ("author__name__invalid",)

        self.assertEqual("Book.author.name is not a relation", cm.exception.args[0])

    def test_override_field_construction_in_resource(self):
        class B(resources.ModelResource):
            class Meta:
                model = Book
                fields = ("published",)

            @classmethod
            def field_from_django_field(self, field_name, django_field, readonly):
                if field_name == "published":
                    return {"sound": "quack"}

        B()
        self.assertEqual({"sound": "quack"}, B.fields["published"])

    def test_readonly_annotated_field_import_and_export(self):
        class B(resources.ModelResource):
            total_categories = fields.Field("total_categories", readonly=True)

            class Meta:
                model = Book
                skip_unchanged = True

        cat1 = Category.objects.create(name="Cat 1")
        self.book.categories.add(cat1)

        resource = B()

        # Verify that the annotated field is correctly exported
        dataset = resource.export(
            queryset=Book.objects.annotate(total_categories=Count("categories"))
        )
        self.assertEqual(int(dataset.dict[0]["total_categories"]), 1)

        # Verify that importing the annotated field raises no errors and that
        # the rows are skipped
        result = resource.import_data(dataset, raise_errors=True)
        self.assertFalse(result.has_errors())
        self.assertEqual(len(result.rows), len(dataset))
        self.assertEqual(result.rows[0].import_type, results.RowResult.IMPORT_TYPE_SKIP)

    def test_follow_relationship_for_modelresource(self):
        class EntryResource(resources.ModelResource):
            username = fields.Field(attribute="user__username", readonly=False)

            class Meta:
                model = Entry
                fields = ("id", "username")

            def after_save_instance(self, instance, row_, **kwargs):
                using_transactions = kwargs.get("using_transactions", False)
                dry_run = kwargs.get("dry_run", False)
                if not using_transactions and dry_run:
                    # we don't have transactions and we want to do a dry_run
                    pass
                else:
                    instance.user.save()

        user = User.objects.create(username="foo")
        entry = Entry.objects.create(user=user)
        row = [
            entry.pk,
            "bar",
        ]
        self.dataset = tablib.Dataset(headers=["id", "username"])
        self.dataset.append(row)
        result = EntryResource().import_data(
            self.dataset, raise_errors=True, dry_run=False
        )
        self.assertFalse(result.has_errors())
        self.assertEqual(User.objects.get(pk=user.pk).username, "bar")

    def test_import_data_dynamic_default_callable(self):
        class DynamicDefaultResource(resources.ModelResource):
            class Meta:
                model = WithDynamicDefault
                fields = (
                    "id",
                    "name",
                )

        self.assertTrue(callable(DynamicDefaultResource.fields["name"].default))

        resource = DynamicDefaultResource()
        dataset = tablib.Dataset(
            headers=[
                "id",
                "name",
            ]
        )
        dataset.append([1, None])
        dataset.append([2, None])
        resource.import_data(dataset, raise_errors=False)
        objs = WithDynamicDefault.objects.all()
        self.assertNotEqual(objs[0].name, objs[1].name)

    def test_float_field(self):
        # 433
        class R(resources.ModelResource):
            class Meta:
                model = WithFloatField

        resource = R()
        dataset = tablib.Dataset(
            headers=[
                "id",
                "f",
            ]
        )
        dataset.append([None, None])
        dataset.append([None, ""])
        resource.import_data(dataset, raise_errors=True)
        self.assertEqual(WithFloatField.objects.all()[0].f, None)
        self.assertEqual(WithFloatField.objects.all()[1].f, None)

    def test_get_db_connection_name(self):
        class BookResource(resources.ModelResource):
            class Meta:
                using_db = "other_db"

        self.assertEqual(BookResource().get_db_connection_name(), "other_db")
        self.assertEqual(CategoryResource().get_db_connection_name(), "default")

    def test_import_data_raises_field_for_wrong_db(self):
        class BookResource(resources.ModelResource):
            class Meta:
                using_db = "wrong_db"

        with self.assertRaises(ConnectionDoesNotExist):
            BookResource().import_data(self.dataset)

    def test_natural_foreign_key_detection(self):
        """
        Test that when the _meta option for use_natural_foreign_keys
        is set on a resource that foreign key widgets are created
        with that flag, and when it's off they are not.
        """

        # For future proof testing, we have one resource with natural
        # foreign keys on, and one off. If the default ever changes
        # this should still work.
        class _BookResource_Unfk(resources.ModelResource):
            class Meta:
                use_natural_foreign_keys = True
                model = Book

        class _BookResource(resources.ModelResource):
            class Meta:
                use_natural_foreign_keys = False
                model = Book

        resource_with_nfks = _BookResource_Unfk()
        author_field_widget = resource_with_nfks.fields["author"].widget
        self.assertTrue(author_field_widget.use_natural_foreign_keys)

        resource_without_nfks = _BookResource()
        author_field_widget = resource_without_nfks.fields["author"].widget
        self.assertFalse(author_field_widget.use_natural_foreign_keys)

    def test_natural_foreign_key_false_positives(self):
        """
        Ensure that if the field's model does not have natural foreign
        key functions, it is not set to use natural foreign keys.
        """
        from django.db import models

        class RelatedModel(models.Model):
            name = models.CharField()

            class Meta:
                app_label = "Test"

        class TestModel(models.Model):
            related_field = models.ForeignKey(RelatedModel, on_delete=models.PROTECT)

            class Meta:
                app_label = "Test"

        class TestModelResource(resources.ModelResource):
            class Meta:
                model = TestModel
                fields = ("id", "related_field")
                use_natural_foreign_keys = True

        resource = TestModelResource()
        related_field_widget = resource.fields["related_field"].widget
        self.assertFalse(related_field_widget.use_natural_foreign_keys)
