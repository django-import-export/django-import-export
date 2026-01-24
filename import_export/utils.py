from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import Manager


class atomic_if_using_transaction:
    """Context manager wraps `atomic` if `using_transactions`.

    Replaces code::

        if using_transactions:
            with transaction.atomic(using=using):
                return something()
        return something()
    """

    def __init__(self, using_transactions, using):
        self.using_transactions = using_transactions
        if using_transactions:
            self.context_manager = transaction.atomic(using=using)

    def __enter__(self):
        if self.using_transactions:
            self.context_manager.__enter__()

    def __exit__(self, *args):
        if self.using_transactions:
            self.context_manager.__exit__(*args)


def get_related_model(field):
    if hasattr(field, "related_model"):
        return field.related_model


def get_lookup_value(instance, attribute):
    """
    Get the value of a (possibly related) attribute from an instance.

    :param instance: Instance object
    :param attribute: Attribute string to lookup
    """
    if attribute is None:
        return None

    attrs = attribute.split("__")
    value = instance

    for attr in attrs:
        try:
            if isinstance(value, dict):
                value = value[attr]
            else:
                value = getattr(value, attr, None)
        except (ValueError, ObjectDoesNotExist, KeyError):
            # needs to have a primary key value before a many-to-many
            # relationship can be used.
            return None
        if value is None:
            return None

        # RelatedManager and ManyRelatedManager classes are callable in
        # Django >= 1.7 but we don't want to call them
    if callable(value) and not isinstance(value, Manager):
        value = value()
    return value
