import tablib
from core.models import Author, Book, Category, Profile
from core.tests.resources import (
    AuthorResource,
    BookResource,
    CategoryResource,
    ProfileResource,
)
from django.test import TransactionTestCase, skipUnlessDBFeature
from django.utils.encoding import force_str
from django.utils.html import strip_tags


class ModelResourceTransactionTest(TransactionTestCase):
    @skipUnlessDBFeature("supports_transactions")
    def test_m2m_import_with_transactions(self):
        resource = BookResource()
        cat1 = Category.objects.create(name="Cat 1")
        headers = ["id", "name", "categories"]
        row = [None, "FooBook", str(cat1.pk)]
        dataset = tablib.Dataset(row, headers=headers)

        result = resource.import_data(dataset, dry_run=True, use_transactions=True)

        row_diff = result.rows[0].diff
        id_diff = row_diff[0]
        # id diff should exist because in rollbacked transaction
        # FooBook has been saved
        self.assertTrue(id_diff)

        categories_diff = row_diff[8]
        self.assertEqual(strip_tags(categories_diff), force_str(cat1.pk))

        # check that it is really rollbacked
        self.assertFalse(Book.objects.filter(name="FooBook"))

    @skipUnlessDBFeature("supports_transactions")
    def test_m2m_import_with_transactions_error(self):
        resource = ProfileResource()
        headers = ["id", "user"]
        # 'user' is a required field, the database will raise an error.
        row = [None, None]
        dataset = tablib.Dataset(row, headers=headers)

        result = resource.import_data(dataset, dry_run=True, use_transactions=True)

        # Ensure the error raised by the database has been saved.
        self.assertTrue(result.has_errors())

        # Ensure the rollback has worked properly.
        self.assertEqual(Profile.objects.count(), 0)

    @skipUnlessDBFeature("supports_transactions")
    def test_integrity_error_rollback_on_savem2m(self):
        # savepoint_rollback() after an IntegrityError gives
        # TransactionManagementError (#399)
        class CategoryResourceRaisesIntegrityError(CategoryResource):
            def save_m2m(self, instance, *args, **kwargs):
                # force raising IntegrityError
                Category.objects.create(name=instance.name)

        resource = CategoryResourceRaisesIntegrityError()
        headers = ["id", "name"]
        rows = [
            [None, "foo"],
        ]
        dataset = tablib.Dataset(*rows, headers=headers)
        result = resource.import_data(
            dataset,
            use_transactions=True,
        )
        self.assertTrue(result.has_errors())

    def test_rollback_on_validation_errors_false(self):
        """Should create only one instance as the second one
        raises a ``ValidationError``"""
        resource = AuthorResource()
        headers = ["id", "name", "birthday"]
        rows = [
            ["", "A.A.Milne", ""],
            ["", "123", "1992test-01-18"],  # raises ValidationError
        ]
        dataset = tablib.Dataset(*rows, headers=headers)
        result = resource.import_data(
            dataset,
            use_transactions=True,
            rollback_on_validation_errors=False,
        )

        # Ensure the validation error raised by the database has been saved.
        self.assertTrue(result.has_validation_errors())

        # Ensure that valid row resulted in an instance created.
        self.assertEqual(Author.objects.count(), 1)

    def test_rollback_on_validation_errors_true(self):
        """
        Should not create any instances as the second one raises a ``ValidationError``
        and ``rollback_on_validation_errors`` flag is set
        """
        resource = AuthorResource()
        headers = ["id", "name", "birthday"]
        rows = [
            ["", "A.A.Milne", ""],
            ["", "123", "1992test-01-18"],  # raises ValidationError
        ]
        dataset = tablib.Dataset(*rows, headers=headers)
        result = resource.import_data(
            dataset,
            use_transactions=True,
            rollback_on_validation_errors=True,
        )

        # Ensure the validation error raised by the database has been saved.
        self.assertTrue(result.has_validation_errors())

        # Ensure the rollback has worked properly, no instances were created.
        self.assertFalse(Author.objects.exists())
