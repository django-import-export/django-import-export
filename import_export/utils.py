from __future__ import unicode_literals

from django.db import transaction


class atomic_if_using_transaction(object):
    """Context manager wraps `atomic` if `using_transactions`.

    Replaces code::

        if using_transactions:
            with transaction.atomic():
                return somethng()
        return something()
    """
    def __init__(self, using_transactions):
        self.using_transactions = using_transactions
        if using_transactions:
            self.context_manager = transaction.atomic()

    def __enter__(self):
        if self.using_transactions:
            self.context_manager.__enter__()

    def __exit__(self, *args):
        if self.using_transactions:
            self.context_manager.__exit__(*args)
