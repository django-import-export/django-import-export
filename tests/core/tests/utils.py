import functools
import warnings


def ignore_widget_deprecation_warning(fn):
    """
    Ignore the specific deprecation warning occurring during Widget.render() execution.
    This can be removed when the deprecation is completed.
    """

    @functools.wraps(fn)
    def inner(*args, **kwargs):
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message=r"^The 'obj' parameter is deprecated and "
                "will be removed in a future release$",
                category=DeprecationWarning,
            )
            fn(*args, **kwargs)

    return inner


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
