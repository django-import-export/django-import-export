import tablib
from core.models import Book, Category, Person, Role, UUIDBook, UUIDCategory
from core.tests.resources import BookResource
from django.contrib.auth.models import User
from django.test import TestCase

from import_export import fields, resources, results, widgets


class ForeignKeyWidgetFollowRelationship(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="foo")
        self.role = Role.objects.create(user=self.user)
        self.person = Person.objects.create(role=self.role)

    def test_export(self):
        class MyPersonResource(resources.ModelResource):
            role = fields.Field(
                column_name="role",
                attribute="role",
                widget=widgets.ForeignKeyWidget(Role, field="user__username"),
            )

            class Meta:
                model = Person
                fields = ["id", "role"]

        resource = MyPersonResource()
        dataset = resource.export(Person.objects.all())
        self.assertEqual(len(dataset), 1)
        self.assertEqual("1", dataset[0][0])
        self.assertEqual("foo", dataset[0][1])

        self.role.user = None
        self.role.save()

        resource = MyPersonResource()
        dataset = resource.export(Person.objects.all())
        self.assertEqual(len(dataset), 1)
        self.assertEqual("1", dataset[0][0])
        self.assertEqual(None, dataset[0][1])


class ManyRelatedManagerDiffTest(TestCase):
    fixtures = ["category", "book", "author"]

    def setUp(self):
        pass

    def test_related_manager_diff(self):
        dataset_headers = ["id", "name", "categories"]
        dataset_row = ["1", "Test Book", "1"]
        original_dataset = tablib.Dataset(headers=dataset_headers)
        original_dataset.append(dataset_row)
        dataset_row[2] = "2"
        changed_dataset = tablib.Dataset(headers=dataset_headers)
        changed_dataset.append(dataset_row)

        book_resource = BookResource()
        export_headers = book_resource.get_export_headers()

        add_result = book_resource.import_data(original_dataset, dry_run=False)
        expected_value = '<ins style="background:#e6ffe6;">1</ins>'
        self.check_value(add_result, export_headers, expected_value)
        change_result = book_resource.import_data(changed_dataset, dry_run=False)
        expected_value = (
            '<del style="background:#ffe6e6;">1</del>'
            '<ins style="background:#e6ffe6;">2</ins>'
        )
        self.check_value(change_result, export_headers, expected_value)

    def check_value(self, result, export_headers, expected_value):
        self.assertEqual(len(result.rows), 1)
        diff = result.rows[0].diff
        self.assertEqual(diff[export_headers.index("categories")], expected_value)


class ManyToManyWidgetDiffTest(TestCase):
    # issue #1270 - ensure ManyToMany fields are correctly checked for
    # changes when skip_unchanged=True
    fixtures = ["category", "book", "author"]

    def setUp(self):
        pass

    def test_many_to_many_widget_create(self):
        # the book is associated with 0 categories
        # when we import a book with category 1, the book
        # should be updated, not skipped
        book = Book.objects.first()
        book.categories.clear()
        dataset_headers = ["id", "name", "categories"]
        dataset_row = [book.id, book.name, "1"]
        dataset = tablib.Dataset(headers=dataset_headers)
        dataset.append(dataset_row)

        book_resource = BookResource()
        book_resource._meta.skip_unchanged = True
        self.assertEqual(0, book.categories.count())

        result = book_resource.import_data(dataset, dry_run=False)

        book.refresh_from_db()
        self.assertEqual(1, book.categories.count())
        self.assertEqual(
            result.rows[0].import_type, results.RowResult.IMPORT_TYPE_UPDATE
        )
        self.assertEqual(Category.objects.first(), book.categories.first())

    def test_many_to_many_widget_create_with_m2m_being_compared(self):
        # issue 1558 - when the object is a new instance and m2m is
        # evaluated for differences
        dataset_headers = ["id", "categories"]
        dataset_row = ["1", "1"]
        dataset = tablib.Dataset(headers=dataset_headers)
        dataset.append(dataset_row)
        book_resource = BookResource()
        book_resource._meta.skip_unchanged = True

        result = book_resource.import_data(dataset, dry_run=False)

        self.assertFalse(result.has_errors())
        self.assertEqual(len(result.rows), 1)
        self.assertEqual(result.rows[0].import_type, results.RowResult.IMPORT_TYPE_NEW)

    def test_many_to_many_widget_update(self):
        # the book is associated with 1 category ('Category 2')
        # when we import a book with category 1, the book
        # should be updated, not skipped, so that Category 2 is replaced by Category 1
        book = Book.objects.first()
        dataset_headers = ["id", "name", "categories"]
        dataset_row = [book.id, book.name, "1"]
        dataset = tablib.Dataset(headers=dataset_headers)
        dataset.append(dataset_row)

        book_resource = BookResource()
        book_resource._meta.skip_unchanged = True
        self.assertEqual(1, book.categories.count())

        result = book_resource.import_data(dataset, dry_run=False)
        self.assertEqual(
            result.rows[0].import_type, results.RowResult.IMPORT_TYPE_UPDATE
        )
        self.assertEqual(1, book.categories.count())
        self.assertEqual(Category.objects.first(), book.categories.first())

    def test_many_to_many_widget_no_changes(self):
        # the book is associated with 1 category ('Category 2')
        # when we import a row with a book with category 1, the book
        # should be skipped, because there is no change
        book = Book.objects.first()
        dataset_headers = ["id", "name", "categories"]
        dataset_row = [book.id, book.name, book.categories.first().id]
        dataset = tablib.Dataset(headers=dataset_headers)
        dataset.append(dataset_row)

        book_resource = BookResource()
        book_resource._meta.skip_unchanged = True

        self.assertEqual(1, book.categories.count())
        result = book_resource.import_data(dataset, dry_run=False)
        self.assertEqual(result.rows[0].import_type, results.RowResult.IMPORT_TYPE_SKIP)
        self.assertEqual(1, book.categories.count())

    def test_many_to_many_widget_handles_ordering(self):
        # the book is associated with 2 categories ('Category 1', 'Category 2')
        # when we import a row with a book with both categories (in any order), the book
        # should be skipped, because there is no change
        book = Book.objects.first()
        self.assertEqual(1, book.categories.count())
        cat1 = Category.objects.get(name="Category 1")
        cat2 = Category.objects.get(name="Category 2")
        book.categories.add(cat1)
        book.save()
        self.assertEqual(2, book.categories.count())
        dataset_headers = ["id", "name", "categories"]

        book_resource = BookResource()
        book_resource._meta.skip_unchanged = True

        # import with natural order
        dataset_row = [book.id, book.name, f"{cat1.id},{cat2.id}"]
        dataset = tablib.Dataset(headers=dataset_headers)
        dataset.append(dataset_row)

        result = book_resource.import_data(dataset, dry_run=False)
        self.assertEqual(result.rows[0].import_type, results.RowResult.IMPORT_TYPE_SKIP)

        # import with reverse order
        dataset_row = [book.id, book.name, f"{cat2.id},{cat1.id}"]
        dataset = tablib.Dataset(headers=dataset_headers)
        dataset.append(dataset_row)

        result = book_resource.import_data(dataset, dry_run=False)
        self.assertEqual(result.rows[0].import_type, results.RowResult.IMPORT_TYPE_SKIP)

        self.assertEqual(2, book.categories.count())

    def test_many_to_many_widget_handles_uuid(self):
        # Test for #1435 - skip_row() handles M2M field when UUID pk used
        class _UUIDBookResource(resources.ModelResource):
            class Meta:
                model = UUIDBook

        uuid_resource = _UUIDBookResource()
        uuid_resource._meta.skip_unchanged = True
        cat1 = UUIDCategory.objects.create(name="Category 1")
        cat2 = UUIDCategory.objects.create(name="Category 2")
        uuid_book = UUIDBook.objects.create(name="uuid book")
        uuid_book.categories.add(cat1, cat2)
        uuid_book.save()

        dataset_headers = ["id", "name", "categories"]
        dataset_row = [uuid_book.id, uuid_book.name, f"{cat1.catid},{cat2.catid}"]
        dataset = tablib.Dataset(headers=dataset_headers)
        dataset.append(dataset_row)
        result = uuid_resource.import_data(dataset, dry_run=False)
        self.assertEqual(result.rows[0].import_type, results.RowResult.IMPORT_TYPE_SKIP)

    def test_skip_row_no_m2m_data_supplied(self):
        # issue #1437
        # test skip_row() when the model defines a m2m field
        # but it is not present in the dataset
        book = Book.objects.first()
        dataset_headers = ["id", "name"]
        dataset_row = [book.id, book.name]
        dataset = tablib.Dataset(headers=dataset_headers)
        dataset.append(dataset_row)

        book_resource = BookResource()
        book_resource._meta.skip_unchanged = True

        self.assertEqual(1, book.categories.count())
        result = book_resource.import_data(dataset, dry_run=False)
        self.assertEqual(result.rows[0].import_type, results.RowResult.IMPORT_TYPE_SKIP)
        self.assertEqual(1, book.categories.count())
