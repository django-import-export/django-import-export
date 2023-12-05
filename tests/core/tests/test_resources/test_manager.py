from unittest import mock

import tablib
from django.contrib.auth.models import User
from django.db.models import CharField
from django.test import TestCase
from test_modelresource.test_postgres import BookResource

from import_export import fields, resources, results, widgets

from ...models import (
    Author,
    Book,
    Category,
    Person,
    Role,
    UUIDBook,
    UUIDCategory,
    WithDefault,
)


class BookResourceWithStoreInstance(resources.ModelResource):
    class Meta:
        model = Book
        store_instance = True


class BookResourceWithLineNumberLogger(BookResource):
    def __init__(self, *args, **kwargs):
        self.before_lines = []
        self.after_lines = []
        return super().__init__(*args, **kwargs)

    def before_import_row(self, row, row_number=None, **kwargs):
        self.before_lines.append(row_number)

    def after_import_row(self, row, row_result, row_number=None, **kwargs):
        self.after_lines.append(row_number)


class WithDefaultResource(resources.ModelResource):
    class Meta:
        model = WithDefault
        fields = ("name",)


class HarshRussianWidget(widgets.CharWidget):
    def clean(self, value, row=None, *args, **kwargs):
        raise ValueError("Ова вриједност је страшна!")


class AuthorResourceWithCustomWidget(resources.ModelResource):
    class Meta:
        model = Author

    @classmethod
    def widget_from_django_field(cls, f, default=widgets.Widget):
        if f.name == "name":
            return HarshRussianWidget
        result = default
        internal_type = (
            f.get_internal_type()
            if callable(getattr(f, "get_internal_type", None))
            else ""
        )
        if internal_type in cls.WIDGETS_MAP:
            result = cls.WIDGETS_MAP[internal_type]
            if isinstance(result, str):
                result = getattr(cls, result)(f)
        return result


class ModelResourceFactoryTest(TestCase):
    def test_create(self):
        BookResource = resources.modelresource_factory(Book)
        self.assertIn("id", BookResource.fields)
        self.assertEqual(BookResource._meta.model, Book)


class WidgetFromDjangoFieldTest(TestCase):
    def test_widget_from_django_field_for_CharField_returns_CharWidget(self):
        f = CharField()
        resource = BookResource()
        w = resource.widget_from_django_field(f)
        self.assertEqual(widgets.CharWidget, w)


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
        self.assertEqual(dataset[0][0], "foo")

        self.role.user = None
        self.role.save()

        resource = MyPersonResource()
        dataset = resource.export(Person.objects.all())
        self.assertEqual(len(dataset), 1)
        self.assertEqual(dataset[0][0], None)


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
        dataset_headers = ["categories"]
        dataset_row = ["1"]
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
        dataset_row = [book.id, book.name, f"{cat1.id}, {cat2.id}"]
        dataset = tablib.Dataset(headers=dataset_headers)
        dataset.append(dataset_row)

        result = book_resource.import_data(dataset, dry_run=False)
        self.assertEqual(result.rows[0].import_type, results.RowResult.IMPORT_TYPE_SKIP)

        # import with reverse order
        dataset_row = [book.id, book.name, f"{cat2.id}, {cat1.id}"]
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
        dataset_row = [uuid_book.id, uuid_book.name, f"{cat1.catid}, {cat2.catid}"]
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


@mock.patch("import_export.resources.Diff", spec=True)
class SkipDiffTest(TestCase):
    """
    Tests that the meta attribute 'skip_diff' means that no diff operations are called.
    'copy.deepcopy' cannot be patched at class level because it causes interferes with
    ``resources.Resource.__init__()``.
    """

    def setUp(self):
        class _BookResource(resources.ModelResource):
            class Meta:
                model = Book
                skip_diff = True

        self.resource = _BookResource()
        self.dataset = tablib.Dataset(headers=["id", "name", "birthday"])
        self.dataset.append(["", "A.A.Milne", "1882test-01-18"])

    def test_skip_diff(self, mock_diff):
        with mock.patch("import_export.resources.deepcopy") as mock_deep_copy:
            self.resource.import_data(self.dataset)
            mock_diff.return_value.compare_with.assert_not_called()
            mock_diff.return_value.as_html.assert_not_called()
            mock_deep_copy.assert_not_called()

    def test_skip_diff_for_delete_new_resource(self, mock_diff):
        class BookResource(resources.ModelResource):
            class Meta:
                model = Book
                skip_diff = True

            def for_delete(self, row, instance):
                return True

        resource = BookResource()
        with mock.patch("import_export.resources.deepcopy") as mock_deep_copy:
            resource.import_data(self.dataset)
            mock_diff.return_value.compare_with.assert_not_called()
            mock_diff.return_value.as_html.assert_not_called()
            mock_deep_copy.assert_not_called()

    def test_skip_diff_for_delete_existing_resource(self, mock_diff):
        book = Book.objects.create()

        class BookResource(resources.ModelResource):
            class Meta:
                model = Book
                skip_diff = True

            def get_or_init_instance(self, instance_loader, row):
                return book, False

            def for_delete(self, row, instance):
                return True

        resource = BookResource()

        with mock.patch("import_export.resources.deepcopy") as mock_deep_copy:
            resource.import_data(self.dataset, dry_run=True)
            mock_diff.return_value.compare_with.assert_not_called()
            mock_diff.return_value.as_html.assert_not_called()
            mock_deep_copy.assert_not_called()

    def test_skip_diff_for_delete_skip_row_not_enabled_new_object(self, mock_diff):
        class BookResource(resources.ModelResource):
            class Meta:
                model = Book
                skip_diff = False

            def for_delete(self, row, instance):
                return True

        resource = BookResource()

        with mock.patch("import_export.resources.deepcopy") as mock_deep_copy:
            resource.import_data(self.dataset, dry_run=True)
            self.assertEqual(1, mock_diff.return_value.compare_with.call_count)
            self.assertEqual(1, mock_deep_copy.call_count)

    def test_skip_row_returns_false_when_skip_diff_is_true(self, mock_diff):
        class BookResource(resources.ModelResource):
            class Meta:
                model = Book
                skip_unchanged = True
                skip_diff = True

        resource = BookResource()

        with mock.patch(
            "import_export.resources.Resource.get_import_fields"
        ) as mock_get_import_fields:
            resource.import_data(self.dataset, dry_run=True)
            self.assertEqual(2, mock_get_import_fields.call_count)


class SkipHtmlDiffTest(TestCase):
    def test_skip_html_diff(self):
        class BookResource(resources.ModelResource):
            class Meta:
                model = Book
                skip_html_diff = True

        resource = BookResource()
        self.dataset = tablib.Dataset(headers=["id", "name", "birthday"])
        self.dataset.append(["", "A.A.Milne", "1882test-01-18"])

        with mock.patch("import_export.resources.Diff.as_html") as mock_as_html:
            resource.import_data(self.dataset, dry_run=True)
            mock_as_html.assert_not_called()


class RawValueTest(TestCase):
    def setUp(self):
        class _BookResource(resources.ModelResource):
            class Meta:
                model = Book
                store_row_values = True

        self.resource = _BookResource()

        self.book = Book.objects.create(name="Some book")
        self.dataset = tablib.Dataset(headers=["id", "name", "author_email", "price"])
        row = [self.book.pk, "Some book", "test@example.com", "10.25"]
        self.dataset.append(row)

    def test_import_data(self):
        result = self.resource.import_data(self.dataset, raise_errors=True)

        self.assertFalse(result.has_errors())
        self.assertEqual(len(result.rows), 1)
        self.assertTrue(result.rows[0].diff)
        self.assertEqual(
            result.rows[0].import_type, results.RowResult.IMPORT_TYPE_UPDATE
        )
        self.assertEqual(result.rows[0].row_values.get("name"), "Some book")
        self.assertEqual(
            result.rows[0].row_values.get("author_email"), "test@example.com"
        )
        self.assertEqual(result.rows[0].row_values.get("price"), "10.25")


class ResourcesHelperFunctionsTest(TestCase):
    """
    Test the helper functions in resources.
    """

    def test_has_natural_foreign_key(self):
        """
        Ensure that resources.has_natural_foreign_key detects correctly
        whether a model has a natural foreign key
        """
        cases = {Book: True, Author: True, Category: False}

        for model, expected_result in cases.items():
            self.assertEqual(resources.has_natural_foreign_key(model), expected_result)
