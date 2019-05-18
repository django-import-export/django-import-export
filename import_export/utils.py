from diff_match_patch import diff_match_patch

from django.conf import settings
from django.db import transaction
from django.utils.encoding import force_text


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


def diff_lines_to_words(text1, text2):
    # Implemented following the docs:
    # https://github.com/google/diff-match-patch/wiki/Line-or-Word-Diffs
    # Only one line is different from diff_linesToChars.
    # line_end = text.find('\n', lineStart)
    # --->
    # line_end = text.find(' ', lineStart)
    # Variable names are also changed to snake_case for code integrity.

    line_array = []
    line_hash = {}
    line_array.append('')

    def diff_lines_to_chars_munge(text):
        chars = []
        line_start = 0
        line_end = -1
        while line_end < len(text) - 1:
            line_end = text.find(' ', line_start)
            if line_end == -1:
                line_end = len(text) - 1
            line = text[line_start:line_end + 1]

            if line in line_hash:
                chars.append(chr(line_hash[line]))
            else:
                if len(line_array) == maxLines:
                    line = text[line_start:]
                    line_end = len(text)
                line_array.append(line)
                line_hash[line] = len(line_array) - 1
                chars.append(chr(len(line_array) - 1))
            line_start = line_end + 1
        return "".join(chars)

    maxLines = 666666
    chars1 = diff_lines_to_chars_munge(text1)
    maxLines = 1114111
    chars2 = diff_lines_to_chars_munge(text2)
    return (chars1, chars2, line_array)


def html_diff(value1, value2, dmp=None):
    dmp = dmp or diff_match_patch()

    value1 = force_text(value1)
    value2 = force_text(value2)
    if getattr(settings, 'IMPORT_EXPORT_DIFF_BY_WORDS', False):
        a = diff_lines_to_words(value1, value2)
        diff = dmp.diff_main(a[0], a[1], False)
        dmp.diff_charsToLines(diff, a[2])
    else:
        diff = dmp.diff_main(value1, value2)

    dmp.diff_cleanupSemantic(diff)
    return dmp.diff_prettyHtml(diff)
