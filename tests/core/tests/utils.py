import functools
import warnings


def ignore_utcnow_deprecation_warning(fn):
    """
    Ignore the specific deprecation warning occurring due to openpyxl and python3.12.
    """

    @functools.wraps(fn)
    def inner(*args, **kwargs):
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                category=DeprecationWarning,
            )
            fn(*args, **kwargs)

    return inner
