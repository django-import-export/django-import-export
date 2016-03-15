from __future__ import unicode_literals

from django.db import transaction

# transaction management for Django < 1.6


def atomic(*args, **kw):
    def noop_decorator(func):
        return func  # pass through

    return noop_decorator


def savepoint(*args, **kwargs):
    transaction.enter_transaction_management()
    transaction.managed(True)


def savepoint_rollback(*args, **kwargs):
    transaction.rollback()
    transaction.leave_transaction_management()


def savepoint_commit(*args, **kwargs):
    transaction.commit()
    transaction.leave_transaction_management()
