from diff_match_patch import diff_match_patch

from django.conf import settings
from django.db import transaction
from django.utils.encoding import force_text

from .diff import diff_lines_to_words


class atomic_if_using_transaction:
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


def html_diff(value1, value2, dmp=None):
    dmp = dmp or diff_match_patch()

    value1 = force_text(value1)
    value2 = force_text(value2)
    if getattr(settings, 'IMPORT_EXPORT_DIFF_BY_CHARS', True):
        diff = dmp.diff_main(value1, value2)
    else:
        a = diff_lines_to_words(value1, value2)
        diff = dmp.diff_main(a[0], a[1], False)
        dmp.diff_charsToLines(diff, a[2])

    dmp.diff_cleanupSemantic(diff)
    return dmp.diff_prettyHtml(diff)
