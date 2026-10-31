from contextlib import contextmanager
from unittest import mock, skipUnless

import tablib
from core.models import Book, Profile, UUIDBook
from django.contrib.auth.models import User
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import DEFAULT_DB_ALIAS, connections
from django.test import TestCase

from import_export import exceptions, fields, resources, widgets
from import_export.instance_loaders import ModelInstanceLoader
from import_export.results import RowResult


class BulkTest(TestCase):
    def setUp(self):
        class _BookResource(resources.ModelResource):
            class Meta:
                model = Book
                use_bulk = True

        self.resource = _BookResource()
        rows = [(i + 1, "book_name") for i in range(10)]
        self.dataset = tablib.Dataset(*rows, headers=["id", "name"])

    def init_update_test_data(self, model=Book):
        [model.objects.create(name="book_name") for _ in range(10)]
        self.assertEqual(10, model.objects.count())
        rows = model.objects.all().values_list("id", "name")
        updated_rows = [(r[0], "UPDATED") for r in rows]
        self.dataset = tablib.Dataset(*updated_rows, headers=["id", "name"])


class BulkCreateTest(BulkTest):
    @mock.patch("core.models.Book.objects.bulk_create")
    def test_bulk_create_does_not_call_object_save(self, mock_bulk_create):
        with mock.patch("core.models.Book.save") as mock_obj_save:
            self.resource.import_data(self.dataset)
            mock_obj_save.assert_not_called()
        mock_bulk_create.assert_called_with(mock.ANY, batch_size=None)

    @mock.patch("core.models.Book.objects.bulk_create")
    def test_bulk_create_batch_size_of_5(self, mock_bulk_create):
        class _BookResource(resources.ModelResource):
            class Meta:
                model = Book
                use_bulk = True
                batch_size = 5

        resource = _BookResource()
        result = resource.import_data(self.dataset)
        self.assertEqual(2, mock_bulk_create.call_count)
        mock_bulk_create.assert_called_with(mock.ANY, batch_size=5)
        self.assertEqual(10, result.total_rows)

    @mock.patch("core.models.UUIDBook.objects.bulk_create")
    def test_bulk_create_uuid_model(self, mock_bulk_create):
        """Test create of a Model which defines uuid not pk (issue #1274)"""

        class _UUIDBookResource(resources.ModelResource):
            class Meta:
                model = UUIDBook
                use_bulk = True
                batch_size = 5
                fields = (
                    "id",
                    "name",
                )

        resource = _UUIDBookResource()
        result = resource.import_data(self.dataset)
        self.assertEqual(2, mock_bulk_create.call_count)
        mock_bulk_create.assert_called_with(mock.ANY, batch_size=5)
        self.assertEqual(10, result.total_rows)

    @mock.patch("core.models.Book.objects.bulk_create")
    def test_bulk_create_no_batch_size(self, mock_bulk_create):
        class _BookResource(resources.ModelResource):
            class Meta:
                model = Book
                use_bulk = True
                batch_size = None

        resource = _BookResource()
        result = resource.import_data(self.dataset)
        self.assertEqual(1, mock_bulk_create.call_count)
        mock_bulk_create.assert_called_with(mock.ANY, batch_size=None)
        self.assertEqual(10, result.total_rows)
        self.assertEqual(10, result.totals["new"])

    @mock.patch("core.models.Book.objects.bulk_create")
    def test_bulk_create_called_dry_run(self, mock_bulk_create):
        class _BookResource(resources.ModelResource):
            class Meta:
                model = Book
                use_bulk = True
                batch_size = None

        resource = _BookResource()
        result = resource.import_data(self.dataset, dry_run=True)
        self.assertEqual(1, mock_bulk_create.call_count)
        self.assertEqual(10, result.total_rows)
        self.assertEqual(10, result.totals["new"])

    @mock.patch("core.models.Book.objects.bulk_create")
    def test_bulk_create_not_called_when_not_using_transactions(self, mock_bulk_create):
        class _BookResource(resources.ModelResource):
            def import_data(
                self,
                dataset,
                dry_run=False,
                raise_errors=False,
                use_transactions=None,
                collect_failed_rows=False,
                **kwargs,
            ):
                # override so that we can enforce not using_transactions
                using_transactions = False
                return self.import_data_inner(
                    dataset,
                    dry_run,
                    raise_errors,
                    using_transactions,
                    collect_failed_rows,
                    **kwargs,
                )

            class Meta:
                model = Book
                use_bulk = True

        resource = _BookResource()
        resource.import_data(self.dataset, dry_run=True)
        mock_bulk_create.assert_not_called()

    @mock.patch("core.models.Book.objects.bulk_create")
    def test_bulk_create_batch_size_of_4(self, mock_bulk_create):
        class _BookResource(resources.ModelResource):
            class Meta:
                model = Book
                use_bulk = True
                batch_size = 4

        resource = _BookResource()
        result = resource.import_data(self.dataset)
        self.assertEqual(3, mock_bulk_create.call_count)
        self.assertEqual(10, result.total_rows)
        self.assertEqual(10, result.totals["new"])

    def test_no_changes_for_errors_if_use_transactions_enabled(self):
        with mock.patch("import_export.results.Result.has_errors") as mock_has_errors:
            mock_has_errors.return_val = True
            self.resource.import_data(self.dataset)
        self.assertEqual(0, Book.objects.count())

    @mock.patch("core.models.Book.objects.bulk_create")
    def test_bulk_create_use_bulk_disabled(self, mock_bulk_create):
        class _BookResource(resources.ModelResource):
            class Meta:
                model = Book
                use_bulk = False

        resource = _BookResource()
        result = resource.import_data(self.dataset)
        mock_bulk_create.assert_not_called()
        self.assertEqual(10, Book.objects.count())
        self.assertEqual(10, result.total_rows)
        self.assertEqual(10, result.totals["new"])

    @mock.patch("core.models.Book.objects.bulk_create")
    def test_bulk_create_bad_batch_size_value(self, mock_bulk_create):
        class _BookResource(resources.ModelResource):
            class Meta:
                model = Book
                use_bulk = True
                batch_size = "a"

        resource = _BookResource()
        with self.assertRaises(ValueError):
            resource.import_data(self.dataset)
        mock_bulk_create.assert_not_called()

    @mock.patch("core.models.Book.objects.bulk_create")
    def test_bulk_create_negative_batch_size_value_negative(self, mock_bulk_create):
        class _BookResource(resources.ModelResource):
            class Meta:
                model = Book
                use_bulk = True
                batch_size = -1

        resource = _BookResource()
        with self.assertRaisesMessage(
            ValueError, "Batch size must be a positive integer"
        ):
            resource.import_data(self.dataset)
        mock_bulk_create.assert_not_called()

    @mock.patch("core.models.Book.objects.bulk_create")
    def test_bulk_create_negative_batch_size_value_0(self, mock_bulk_create):
        class _BookResource(resources.ModelResource):
            class Meta:
                model = Book
                use_bulk = True
                batch_size = 0

        resource = _BookResource()
        with self.assertRaisesMessage(
            ValueError, "Batch size must be a positive integer"
        ):
            resource.import_data(self.dataset)
        mock_bulk_create.assert_not_called()

    @mock.patch("core.models.Book.objects.bulk_create")
    def test_bulk_create_oversized_batch_size_value(self, mock_bulk_create):
        class _BookResource(resources.ModelResource):
            class Meta:
                model = Book
                use_bulk = True
                batch_size = 100

        resource = _BookResource()
        result = resource.import_data(self.dataset)
        self.assertEqual(1, mock_bulk_create.call_count)
        mock_bulk_create.assert_called_with(mock.ANY, batch_size=None)
        self.assertEqual(10, result.total_rows)
        self.assertEqual(10, result.totals["new"])

    @mock.patch("core.models.Book.objects.bulk_create")
    def test_bulk_create_logs_exception(self, mock_bulk_create):
        e = ValidationError("invalid field")
        mock_bulk_create.side_effect = e

        class _BookResource(resources.ModelResource):
            class Meta:
                model = Book
                use_bulk = True
                batch_size = 100

        resource = _BookResource()
        with mock.patch("logging.Logger.debug") as mock_exception:
            resource.import_data(self.dataset)
            mock_exception.assert_called_with(e, exc_info=e)

    @mock.patch("core.models.Book.objects.bulk_create")
    def test_bulk_create_raises_exception(self, mock_bulk_create):
        mock_bulk_create.side_effect = ValidationError("invalid field")

        class _BookResource(resources.ModelResource):
            class Meta:
                model = Book
                use_bulk = True
                batch_size = 100

        resource = _BookResource()
        with self.assertRaises(exceptions.ImportError):
            resource.import_data(self.dataset, raise_errors=True)

    @mock.patch("core.models.Book.objects.bulk_create")
    def test_bulk_create_exception_gathered_on_dry_run(self, mock_bulk_create):
        mock_bulk_create.side_effect = ValidationError("invalid field")

        class _BookResource(resources.ModelResource):
            class Meta:
                model = Book
                use_bulk = True
                batch_size = 100

        resource = _BookResource()
        result = resource.import_data(self.dataset, dry_run=True, raise_errors=False)
        self.assertTrue(result.has_errors())

    def test_m2m_not_called_for_bulk(self):
        mock_m2m_widget = mock.Mock(spec=widgets.ManyToManyWidget)

        class BookM2MResource(resources.ModelResource):
            categories = fields.Field(attribute="categories", widget=mock_m2m_widget)

            class Meta:
                model = Book
                use_bulk = True

        resource = BookM2MResource()
        self.dataset.append_col(["Cat 1|Cat 2"] * 10, header="categories")
        resource.import_data(self.dataset, raise_errors=True)
        mock_m2m_widget.assert_not_called()

    def test_force_init_instance(self):
        class _BookResource(resources.ModelResource):
            def get_instance(self, instance_loader, row):
                raise AssertionError("should not be called")

            class Meta:
                model = Book
                force_init_instance = True

        resource = _BookResource()
        self.assertIsNotNone(
            resource.get_or_init_instance(
                ModelInstanceLoader(resource), self.dataset[0]
            )
        )

    @mock.patch("import_export.resources.atomic_if_using_transaction")
    def test_no_sub_transaction_on_row_for_bulk(self, mock_atomic_if_using_transaction):
        class _BookResource(resources.ModelResource):
            class Meta:
                model = Book
                use_bulk = True

        resource = _BookResource()
        resource.import_data(self.dataset)
        self.assertIn(
            False, [x[0][0] for x in mock_atomic_if_using_transaction.call_args_list]
        )


class BulkCreateUpdateConflictsTest(BulkTest):
    """``update_conflicts`` makes a bulk import an upsert (issue #2049)."""

    @contextmanager
    def _conflict_target_support(self, resource, supported):
        # whether a conflict target is sent is a property of the backend, so the
        # tests which assert on it pin the feature rather than read it
        connection = connections[resource.get_db_connection_name()]
        with mock.patch.object(
            connection.features, "supports_update_conflicts_with_target", supported
        ):
            yield

    @mock.patch("core.models.Book.objects.bulk_create")
    def test_update_conflicts_passed_to_bulk_create(self, mock_bulk_create):
        class _BookResource(resources.ModelResource):
            class Meta:
                model = Book
                use_bulk = True
                update_conflicts = True

        resource = _BookResource()
        with self._conflict_target_support(resource, True):
            resource.import_data(self.dataset)
        mock_bulk_create.assert_called_with(
            mock.ANY,
            batch_size=None,
            update_conflicts=True,
            # defaults: the imported columns except the import_id_fields,
            # which identify the conflicting row and so are the conflict
            # target; columns absent from the dataset ("id,name" here) are
            # left out so that their model defaults are not written back
            update_fields=["name"],
            unique_fields=["id"],
        )

    @mock.patch("core.models.Book.objects.bulk_create")
    def test_update_conflicts_not_passed_when_disabled(self, mock_bulk_create):
        self.resource.import_data(self.dataset)
        mock_bulk_create.assert_called_with(mock.ANY, batch_size=None)

    @mock.patch("core.models.Book.objects.bulk_create")
    def test_update_fields_and_unique_fields_can_be_declared(self, mock_bulk_create):
        class _BookResource(resources.ModelResource):
            class Meta:
                model = Book
                use_bulk = True
                update_conflicts = True
                update_fields = ["name"]
                unique_fields = ["id"]

        resource = _BookResource()
        with self._conflict_target_support(resource, True):
            resource.import_data(self.dataset)
        mock_bulk_create.assert_called_with(
            mock.ANY,
            batch_size=None,
            update_conflicts=True,
            update_fields=["name"],
            unique_fields=["id"],
        )

    @mock.patch("core.models.Book.objects.bulk_create")
    def test_unique_fields_omitted_when_backend_has_no_conflict_target(
        self, mock_bulk_create
    ):
        # MySQL and MariaDB update every unique constraint and reject a
        # conflict target, so no unique_fields must be sent there.
        class _BookResource(resources.ModelResource):
            class Meta:
                model = Book
                use_bulk = True
                update_conflicts = True

        resource = _BookResource()
        with self._conflict_target_support(resource, False):
            resource.import_data(self.dataset)
        mock_bulk_create.assert_called_with(
            mock.ANY,
            batch_size=None,
            update_conflicts=True,
            update_fields=["name"],
        )

    def test_default_update_fields_exclude_m2m_and_primary_key(self):
        # outside an import there is no dataset to limit the defaults to, so
        # this is every writable field; it must still not include a
        # many-to-many field (Django rejects non-concrete update_fields) or
        # the pk (rejected outright) when rows are identified by a natural
        # key and the pk remains in the resource fields.
        class _BookResource(resources.ModelResource):
            class Meta:
                model = Book
                use_bulk = True
                update_conflicts = True
                import_id_fields = ("name",)

        self.assertEqual(
            [
                "author_id",
                "author_email",
                "imported",
                "published",
                "published_time",
                "price",
                "added",
            ],
            _BookResource().get_bulk_create_update_fields(),
        )

    def test_default_unique_fields_are_the_import_id_fields(self):
        class _ProfileResource(resources.ModelResource):
            class Meta:
                model = Profile
                use_bulk = True
                update_conflicts = True
                import_id_fields = ("user",)

        resource = _ProfileResource()
        with self._conflict_target_support(resource, True):
            self.assertEqual(
                ["user_id"], resource.get_bulk_create_kwargs()["unique_fields"]
            )

    @mock.patch("core.models.Book.objects.bulk_create")
    def test_non_model_attribute_not_in_default_update_fields(self, mock_bulk_create):
        # bulk_create() resolves every update_fields name to a model field, so
        # a resource field backed by a plain attribute would fail every batch
        class _BookResource(resources.ModelResource):
            shelf = fields.Field(attribute="shelf", column_name="shelf")

            class Meta:
                model = Book
                fields = ("id", "name", "shelf")
                use_bulk = True
                update_conflicts = True

        dataset = tablib.Dataset((1, "book", "A3"), headers=["id", "name", "shelf"])
        resource = _BookResource()
        with self._conflict_target_support(resource, True):
            resource.import_data(dataset, raise_errors=True)
        self.assertEqual(["name"], mock_bulk_create.call_args.kwargs["update_fields"])

    def test_string_options_rejected(self):
        for option in ("update_fields", "unique_fields"):
            with self.subTest(option=option):
                meta = type(
                    "Meta",
                    (),
                    {
                        "model": Book,
                        "use_bulk": True,
                        "update_conflicts": True,
                        option: "name",
                    },
                )
                resource_class = type(
                    "_BookResource", (resources.ModelResource,), {"Meta": meta}
                )
                with self.assertRaisesRegex(
                    ImproperlyConfigured, f"{option} must be a list or tuple"
                ):
                    resource_class().import_data(self.dataset, raise_errors=True)

    def test_unique_fields_without_unique_constraint_rejected(self):
        # Postgres and SQLite need a unique constraint on the conflict target,
        # and Book.name has none; fail before importing rather than per batch
        class _BookResource(resources.ModelResource):
            class Meta:
                model = Book
                use_bulk = True
                update_conflicts = True
                import_id_fields = ("name",)

        dataset = tablib.Dataset(("book", "9.99"), headers=["name", "price"])
        resource = _BookResource()
        with self._conflict_target_support(resource, True):
            with self.assertRaisesRegex(
                ImproperlyConfigured, "do not match a unique constraint"
            ):
                resource.import_data(dataset, raise_errors=True)
        self.assertEqual(0, Book.objects.count())

    def test_unique_fields_not_checked_without_conflict_target(self):
        # MySQL and MariaDB are not sent a target, so there is nothing to match
        class _BookResource(resources.ModelResource):
            class Meta:
                model = Book
                use_bulk = True
                update_conflicts = True
                import_id_fields = ("name",)

        dataset = tablib.Dataset(("book", "9.99"), headers=["name", "price"])
        resource = _BookResource()
        with self._conflict_target_support(resource, False):
            with mock.patch("core.models.Book.objects.bulk_create") as bulk_create:
                resource.import_data(dataset, raise_errors=True)
        self.assertNotIn("unique_fields", bulk_create.call_args.kwargs)

    def test_empty_update_fields_rejected(self):
        class _BookResource(resources.ModelResource):
            class Meta:
                model = Book
                fields = ("id", "name")
                import_id_fields = ("id", "name")
                use_bulk = True
                update_conflicts = True

        with self.assertRaisesRegex(
            ImproperlyConfigured, "needs at least one field to update"
        ):
            _BookResource().import_data(self.dataset, raise_errors=True)

    def test_backend_without_update_conflicts_rejected(self):
        class _BookResource(resources.ModelResource):
            class Meta:
                model = Book
                use_bulk = True
                update_conflicts = True

        resource = _BookResource()
        connection = connections[resource.get_db_connection_name()]
        with mock.patch.object(connection.features, "supports_update_conflicts", False):
            with self.assertRaisesRegex(ValueError, "not supported"):
                resource.import_data(self.dataset, raise_errors=True)
        self.assertEqual(0, Book.objects.count())

    def test_unique_fields_naming_no_model_field_rejected(self):
        class _BookResource(resources.ModelResource):
            class Meta:
                model = Book
                use_bulk = True
                update_conflicts = True
                unique_fields = ["shelf"]

        resource = _BookResource()
        with self._conflict_target_support(resource, True):
            with self.assertRaisesRegex(
                ImproperlyConfigured, "do not match a unique constraint"
            ):
                resource.import_data(self.dataset, raise_errors=True)

    def test_empty_unique_fields_rejected(self):
        class _BookResource(resources.ModelResource):
            class Meta:
                model = Book
                use_bulk = True
                update_conflicts = True
                unique_fields = []

        with self.assertRaisesRegex(ImproperlyConfigured, "needs a conflict target"):
            _BookResource().import_data(self.dataset, raise_errors=True)

    @mock.patch("core.models.Book.objects.bulk_create")
    def test_composite_conflict_target_reclassifies_rows(self, mock_bulk_create):
        # no test model has a composite unique constraint, so this goes through
        # the MySQL-style path, where the target is not validated or sent; the
        # existence query on both fields still runs against the database
        book = Book.objects.create(name="stored")

        class _BookResource(resources.ModelResource):
            class Meta:
                model = Book
                fields = ("id", "name", "price")
                use_bulk = True
                force_init_instance = True
                update_conflicts = True
                unique_fields = ["id", "name"]

        dataset = tablib.Dataset(
            (book.pk, "stored", "1.00"),
            (book.pk, "renamed", "2.00"),
            headers=["id", "name", "price"],
        )
        resource = _BookResource()
        with self._conflict_target_support(resource, False):
            result = resource.import_data(dataset, raise_errors=True)

        self.assertEqual(
            [RowResult.IMPORT_TYPE_UPDATE, RowResult.IMPORT_TYPE_NEW],
            [row.import_type for row in result.rows],
        )

    def test_feature_detection_uses_write_database(self):
        # bulk_create() is not routed through Meta.using_db, so the features
        # checked must be those of the database it actually writes to, not of
        # the using_db alias (which is not even configured here)
        class _BookResource(resources.ModelResource):
            class Meta:
                model = Book
                use_bulk = True
                update_conflicts = True
                using_db = "not-configured"

        kwargs = _BookResource().get_bulk_create_kwargs()
        self.assertTrue(kwargs["update_conflicts"])

    def test_update_conflicts_requires_use_bulk(self):
        class _BookResource(resources.ModelResource):
            class Meta:
                model = Book
                update_conflicts = True

        with self.assertRaisesRegex(ValueError, "update_conflicts requires use_bulk"):
            _BookResource().import_data(self.dataset, raise_errors=True)


@skipUnless(
    connections[DEFAULT_DB_ALIAS].features.supports_update_conflicts,
    "backend does not support updating conflicts",
)
class BulkCreateUpdateConflictsIntegrationTest(TestCase):
    """The upsert against a real database, rather than a mocked bulk_create.

    ``force_init_instance`` skips the existence check, so every row is created
    and a row whose id is already present conflicts on insert.
    """

    class _BookResource(resources.ModelResource):
        class Meta:
            model = Book
            fields = ("id", "name")
            use_bulk = True
            force_init_instance = True
            update_conflicts = True

    class _ConflictingBookResource(_BookResource):
        class Meta:
            update_conflicts = False

    def setUp(self):
        self.book = Book.objects.create(name="original")
        self.dataset = tablib.Dataset((self.book.pk, "updated"), headers=["id", "name"])

    def test_conflicting_row_is_updated(self):
        result = self._BookResource().import_data(self.dataset, raise_errors=True)

        self.assertFalse(result.has_errors())
        self.assertEqual(1, Book.objects.count())
        self.book.refresh_from_db()
        self.assertEqual("updated", self.book.name)

    def test_conflicting_row_errors_without_update_conflicts(self):
        # raise_errors, so that the failed insert unwinds through the atomic
        # block rather than being collected on the result. A backend which
        # aborts the transaction on error, such as Postgres, rejects every
        # statement until the block is left, including the release of the
        # savepoint the block ends with.
        with self.assertRaises(exceptions.ImportError):
            self._ConflictingBookResource().import_data(self.dataset, raise_errors=True)

        self.book.refresh_from_db()
        self.assertEqual("original", self.book.name)

    def test_default_update_fields_skip_many_to_many(self):
        # all of Book's fields, so the default update_fields would include the
        # "categories" many-to-many field if it were not filtered out, and
        # Django rejects that
        class _AllFieldsBookResource(resources.ModelResource):
            class Meta:
                model = Book
                use_bulk = True
                force_init_instance = True
                update_conflicts = True

        result = _AllFieldsBookResource().import_data(self.dataset, raise_errors=True)

        self.assertFalse(result.has_errors())
        self.assertEqual(1, Book.objects.count())
        self.book.refresh_from_db()
        self.assertEqual("updated", self.book.name)

    def test_default_update_fields_skip_pk_with_natural_key(self):
        # rows are identified by the unique "user" field, and the pk stays in
        # the resource fields, so the default update_fields would include it
        # if it were not filtered out, and Django rejects that
        class _ProfileResource(resources.ModelResource):
            class Meta:
                model = Profile
                fields = ("id", "user", "is_private")
                import_id_fields = ("user",)
                use_bulk = True
                force_init_instance = True
                update_conflicts = True

        user = User.objects.create_user("profile-user")
        profile = Profile.objects.create(user=user, is_private=True)
        dataset = tablib.Dataset((user.pk, 0), headers=["user", "is_private"])

        result = _ProfileResource().import_data(dataset, raise_errors=True)

        self.assertFalse(result.has_errors())
        self.assertEqual(1, Profile.objects.count())
        profile.refresh_from_db()
        self.assertFalse(profile.is_private)

    def test_partial_column_import_keeps_absent_fields(self):
        # the dataset only carries id and name; the other fields must keep
        # their stored values rather than be reset to the model defaults
        self.book.author_email = "author@example.com"
        self.book.price = "9.99"
        self.book.imported = True
        self.book.save()

        class _PartialBookResource(resources.ModelResource):
            class Meta:
                model = Book
                use_bulk = True
                force_init_instance = True
                update_conflicts = True

        result = _PartialBookResource().import_data(self.dataset, raise_errors=True)

        self.assertFalse(result.has_errors())
        self.book.refresh_from_db()
        self.assertEqual("updated", self.book.name)
        self.assertEqual("author@example.com", self.book.author_email)
        self.assertEqual("9.99", str(self.book.price))
        self.assertTrue(self.book.imported)

    def test_upserted_rows_reported_as_updates(self):
        new_id = self.book.pk + 100
        dataset = tablib.Dataset(
            (self.book.pk, "updated"), (new_id, "added"), headers=["id", "name"]
        )
        for batch_size in (1, 2, 1000):
            with self.subTest(batch_size=batch_size):

                class _BatchedBookResource(self._BookResource):
                    class Meta:
                        pass

                _BatchedBookResource._meta.batch_size = batch_size
                result = _BatchedBookResource().import_data(dataset, raise_errors=True)

                self.assertEqual(
                    [RowResult.IMPORT_TYPE_UPDATE, RowResult.IMPORT_TYPE_NEW],
                    [row.import_type for row in result.rows],
                )
                self.assertEqual(1, result.totals[RowResult.IMPORT_TYPE_UPDATE])
                self.assertEqual(1, result.totals[RowResult.IMPORT_TYPE_NEW])
                # the second subtest finds both rows stored
                dataset = tablib.Dataset(
                    (self.book.pk, "updated"), (new_id, "added"), headers=["id", "name"]
                )
                Book.objects.filter(pk=new_id).delete()

    def test_upserted_rows_reported_as_updates_on_dry_run(self):
        result = self._BookResource().import_data(self.dataset, dry_run=True)

        self.assertEqual(1, result.totals[RowResult.IMPORT_TYPE_UPDATE])
        self.assertEqual(0, result.totals[RowResult.IMPORT_TYPE_NEW])
        self.book.refresh_from_db()
        self.assertEqual("original", self.book.name)

    def test_rows_without_a_key_reported_as_new(self):
        # a null never conflicts, so a row with no id is always an insert
        dataset = tablib.Dataset(("", "added"), headers=["id", "name"])

        result = self._BookResource().import_data(dataset, raise_errors=True)

        self.assertEqual(1, result.totals[RowResult.IMPORT_TYPE_NEW])
        self.assertEqual(2, Book.objects.count())

    def test_sequences_not_reset_when_every_row_is_an_upsert(self):
        # the reset is only needed when rows with explicit pks were inserted,
        # and running it on every upsert reintroduces the race of #2166
        connection = connections[DEFAULT_DB_ALIAS]
        with mock.patch.object(
            connection.ops, "sequence_reset_sql", return_value=[]
        ) as sequence_reset_sql:
            self._BookResource().import_data(self.dataset, raise_errors=True)
        sequence_reset_sql.assert_not_called()


class BulkUpdateTest(BulkTest):
    class _BookResource(resources.ModelResource):
        class Meta:
            model = Book
            use_bulk = True
            fields = ("id", "name")
            import_id_fields = ("id",)

    def setUp(self):
        super().setUp()
        self.init_update_test_data()
        self.resource = self._BookResource()

    def test_bulk_update(self):
        self.assertEqual(["name"], self.resource.get_bulk_update_fields())
        result = self.resource.import_data(self.dataset)
        [self.assertEqual("UPDATED", b.name) for b in Book.objects.all()]
        self.assertEqual(10, result.total_rows)
        self.assertEqual(10, result.totals["update"])

    @mock.patch("core.models.Book.objects.bulk_update")
    def test_bulk_update_batch_size_of_4(self, mock_bulk_update):
        class _BookResource(resources.ModelResource):
            class Meta:
                model = Book
                use_bulk = True
                batch_size = 4

        resource = _BookResource()
        self.assertEqual(
            [
                "name",
                "author_id",
                "author_email",
                "imported",
                "published",
                "published_time",
                "price",
                "added",
                "categories",
            ],
            resource.get_bulk_update_fields(),
        )
        result = resource.import_data(self.dataset)
        self.assertEqual(3, mock_bulk_update.call_count)
        self.assertEqual(10, result.total_rows)
        self.assertEqual(10, result.totals["update"])

    @mock.patch("core.models.Book.objects.bulk_update")
    def test_bulk_update_batch_size_of_5(self, mock_bulk_update):
        class _BookResource(resources.ModelResource):
            class Meta:
                model = Book
                use_bulk = True
                batch_size = 5

        resource = _BookResource()
        result = resource.import_data(self.dataset)
        self.assertEqual(2, mock_bulk_update.call_count)
        self.assertEqual(10, result.total_rows)
        self.assertEqual(10, result.totals["update"])

    @mock.patch("core.models.Book.objects.bulk_update")
    def test_bulk_update_no_batch_size(self, mock_bulk_update):
        class _BookResource(resources.ModelResource):
            class Meta:
                model = Book
                use_bulk = True
                batch_size = None

        resource = _BookResource()
        result = resource.import_data(self.dataset)
        self.assertEqual(1, mock_bulk_update.call_count)
        mock_bulk_update.assert_called_with(mock.ANY, mock.ANY, batch_size=None)
        self.assertEqual(10, result.total_rows)
        self.assertEqual(10, result.totals["update"])

    @mock.patch("core.models.Book.objects.bulk_update")
    def test_bulk_update_not_called_when_not_using_transactions(self, mock_bulk_update):
        class _BookResource(resources.ModelResource):
            def import_data(
                self,
                dataset,
                dry_run=False,
                raise_errors=False,
                use_transactions=None,
                collect_failed_rows=False,
                **kwargs,
            ):
                # override so that we can enforce not using_transactions
                using_transactions = False
                return self.import_data_inner(
                    dataset,
                    dry_run,
                    raise_errors,
                    using_transactions,
                    collect_failed_rows,
                    **kwargs,
                )

            class Meta:
                model = Book
                use_bulk = True

        resource = _BookResource()
        resource.import_data(self.dataset, dry_run=True)
        mock_bulk_update.assert_not_called()

    @mock.patch("core.models.Book.objects.bulk_update")
    def test_bulk_update_called_for_dry_run(self, mock_bulk_update):
        self.resource.import_data(self.dataset, dry_run=True)
        self.assertEqual(1, mock_bulk_update.call_count)

    @mock.patch("core.models.Book.objects.bulk_update")
    def test_bulk_not_called_when_use_bulk_disabled(self, mock_bulk_update):
        class _BookResource(resources.ModelResource):
            class Meta:
                model = Book
                use_bulk = False

        resource = _BookResource()
        result = resource.import_data(self.dataset)
        self.assertEqual(10, Book.objects.count())
        self.assertEqual(10, result.total_rows)
        self.assertEqual(10, result.totals["update"])
        mock_bulk_update.assert_not_called()

    @mock.patch("core.models.Book.objects.bulk_update")
    def test_bulk_update_logs_exception(self, mock_bulk_update):
        e = ValidationError("invalid field")
        mock_bulk_update.side_effect = e

        class _BookResource(resources.ModelResource):
            class Meta:
                model = Book
                use_bulk = True

        resource = _BookResource()
        with mock.patch("logging.Logger.debug") as mock_exception:
            resource.import_data(self.dataset)
            mock_exception.assert_called_with(e, exc_info=e)

    @mock.patch("core.models.Book.objects.bulk_update")
    def test_bulk_update_raises_exception(self, mock_bulk_update):
        e = ValidationError("invalid field")
        mock_bulk_update.side_effect = e

        class _BookResource(resources.ModelResource):
            class Meta:
                model = Book
                use_bulk = True

        resource = _BookResource()
        with self.assertRaises(exceptions.ImportError) as raised_exc:
            resource.import_data(self.dataset, raise_errors=True)
            self.assertEqual(e, raised_exc)

    def test_bulk_update_with_different_name_than_attribute(self):
        class _BookResource(resources.ModelResource):
            name_field = fields.Field(attribute="name", column_name="name")

            class Meta:
                model = Book
                use_bulk = True
                fields = ("id", "name_field")
                import_id_fields = ("id",)

        resource = _BookResource()
        self.assertEqual(["name"], resource.get_bulk_update_fields())
        result = resource.import_data(self.dataset)
        self.assertEqual(10, result.total_rows)
        self.assertEqual(10, result.totals["update"])
        self.assertEqual(10, Book.objects.filter(name="UPDATED").count())

    def test_bulk_update_with_readonly_field(self):
        class _BookResource(resources.ModelResource):
            name = fields.Field(attribute="name", column_name="name", readonly=True)

            class Meta:
                model = Book
                use_bulk = True
                fields = ("id", "name")
                import_id_fields = ("id",)
                skip_unchanged = True

        resource = _BookResource()
        self.assertEqual([], resource.get_bulk_update_fields())
        result = resource.import_data(self.dataset)
        self.assertEqual(10, result.total_rows)
        self.assertEqual(0, result.totals["update"])
        self.assertEqual(10, Book.objects.filter(name="book_name").count())

    def test_bulk_update_with_related_field(self):
        class _BookResource(resources.ModelResource):
            author__name = fields.Field(
                attribute="author__name", column_name="author_name"
            )

            class Meta:
                model = Book
                use_bulk = True
                fields = ("id", "author__name")
                import_id_fields = ("id",)
                skip_unchanged = True

        resource = _BookResource()
        self.assertEqual([], resource.get_bulk_update_fields())
        result = resource.import_data(self.dataset)
        self.assertEqual(10, result.total_rows)
        self.assertEqual(0, result.totals["update"])


class BulkUUIDBookUpdateTest(BulkTest):
    def setUp(self):
        super().setUp()
        self.init_update_test_data(model=UUIDBook)

    @mock.patch("core.models.UUIDBook.objects.bulk_update")
    def test_bulk_update_uuid_model(self, mock_bulk_update):
        """Test update of a Model which defines uuid not pk (issue #1274)"""

        class _UUIDBookResource(resources.ModelResource):
            class Meta:
                model = UUIDBook
                use_bulk = True
                batch_size = 5
                fields = (
                    "id",
                    "name",
                )

        resource = _UUIDBookResource()
        result = resource.import_data(self.dataset)
        self.assertEqual(2, mock_bulk_update.call_count)
        self.assertEqual(10, result.total_rows)
        self.assertEqual(10, result.totals["update"])


class BulkDeleteTest(BulkTest):
    class DeleteBookResource(resources.ModelResource):
        def for_delete(self, row, instance):
            return True

        class Meta:
            model = Book
            use_bulk = True
            # there are errors when diffing with mocks
            # therefore disable diff with this flag
            skip_diff = True

    def setUp(self):
        super().setUp()
        self.resource = self.DeleteBookResource()
        self.resource._meta.batch_size = 1000
        self.resource._meta.use_bulk = True
        self.init_update_test_data()

    @mock.patch("core.models.Book.delete")
    def test_bulk_delete_use_bulk_is_false(self, mock_obj_delete):
        self.resource._meta.use_bulk = False
        self.resource.import_data(self.dataset)
        self.assertEqual(10, mock_obj_delete.call_count)

    @mock.patch("core.models.Book.objects")
    def test_bulk_delete_batch_size_of_4(self, mock_obj_manager):
        self.resource._meta.batch_size = 4
        result = self.resource.import_data(self.dataset)
        self.assertEqual(3, mock_obj_manager.filter.return_value.delete.call_count)
        self.assertEqual(10, result.total_rows)
        self.assertEqual(10, result.totals["delete"])

    @mock.patch("core.models.Book.objects")
    def test_bulk_delete_batch_size_of_5(self, mock_obj_manager):
        self.resource._meta.batch_size = 5
        result = self.resource.import_data(self.dataset)
        self.assertEqual(2, mock_obj_manager.filter.return_value.delete.call_count)
        self.assertEqual(10, result.total_rows)
        self.assertEqual(10, result.totals["delete"])

    @mock.patch("core.models.Book.objects")
    def test_bulk_delete_batch_size_is_none(self, mock_obj_manager):
        self.resource._meta.batch_size = None
        result = self.resource.import_data(self.dataset)
        self.assertEqual(1, mock_obj_manager.filter.return_value.delete.call_count)
        self.assertEqual(10, result.total_rows)
        self.assertEqual(10, result.totals["delete"])

    @mock.patch("core.models.Book.objects")
    def test_bulk_delete_not_called_when_not_using_transactions(self, mock_obj_manager):
        class _BookResource(self.DeleteBookResource):
            def import_data(
                self,
                dataset,
                dry_run=False,
                raise_errors=False,
                use_transactions=None,
                collect_failed_rows=False,
                **kwargs,
            ):
                # override so that we can enforce not using_transactions
                using_transactions = False
                return self.import_data_inner(
                    dataset,
                    dry_run,
                    raise_errors,
                    using_transactions,
                    collect_failed_rows,
                    **kwargs,
                )

        resource = _BookResource()
        resource.import_data(self.dataset, dry_run=True)
        self.assertEqual(0, mock_obj_manager.filter.return_value.delete.call_count)

    @mock.patch("core.models.Book.objects")
    def test_bulk_delete_called_for_dry_run(self, mock_obj_manager):
        self.resource.import_data(self.dataset, dry_run=True)
        self.assertEqual(1, mock_obj_manager.filter.return_value.delete.call_count)

    @mock.patch("core.models.Book.objects")
    def test_bulk_delete_logs_exception(self, mock_obj_manager):
        e = Exception("invalid")
        mock_obj_manager.filter.return_value.delete.side_effect = e

        with mock.patch("logging.Logger.debug") as mock_exception:
            self.resource.import_data(self.dataset)
            mock_exception.assert_called_with(e, exc_info=mock.ANY)
            self.assertEqual(1, mock_exception.call_count)

    @mock.patch("core.models.Book.objects")
    def test_bulk_delete_raises_exception(self, mock_obj_manager):
        e = Exception("invalid")
        mock_obj_manager.filter.return_value.delete.side_effect = e

        with self.assertRaises(Exception) as raised_exc:
            self.resource.import_data(self.dataset, raise_errors=True)
            self.assertEqual(e, raised_exc)


class BulkUUIDBookDeleteTest(BulkTest):
    class DeleteBookResource(resources.ModelResource):
        def for_delete(self, row, instance):
            return True

        class Meta:
            model = UUIDBook
            use_bulk = True
            batch_size = 5

    def setUp(self):
        super().setUp()
        self.resource = self.DeleteBookResource()
        self.init_update_test_data(model=UUIDBook)

    def test_bulk_delete_batch_size_of_5(self):
        self.assertEqual(10, UUIDBook.objects.count())
        self.resource.import_data(self.dataset)
        self.assertEqual(0, UUIDBook.objects.count())
