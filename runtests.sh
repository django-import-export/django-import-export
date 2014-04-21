tests=${@:-core}
PYTHONPATH=".:tests:$PYTHONPATH" django-admin.py test --settings=settings $tests
