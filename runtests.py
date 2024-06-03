"""
Helper script to generate coverage data only if running in CI.
This script is called from tox (see tox.ini).
Coverage files are generated only if a `COVERAGE` environment variable is present.
This is necessary to prevent unwanted coverage files when running locally (issue #1424)
"""
import os


def main():
    coverage_args = "-m coverage run" if os.environ.get("COVERAGE") else ""

    retval = os.system(
        "python -W error::DeprecationWarning -W error::PendingDeprecationWarning "
        f"{coverage_args} "
        "./tests/manage.py test core --settings=settings"
    )
    if retval != 0:
        exit(1)
    exit(0)


if __name__ == "__main__":
    main()
