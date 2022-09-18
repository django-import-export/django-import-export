from django.db import transaction


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


def original(method):
    """
    A decorator used to mark some class methods as 'original',
    making it easy to detect whether they have been overridden
    by a subclass. Useful for method deprecation.
    """
    method.is_original = True
    return method
