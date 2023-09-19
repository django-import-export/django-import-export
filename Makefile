.PHONY: clean-pyc clean-build docs help
.PHONY: lint test coverage test-codecov
.DEFAULT_GOAL := help
RUN_TEST_COMMAND=PYTHONPATH=".:tests:${PYTHONPATH}" django-admin test core --settings=settings
help:
	@grep '^[a-zA-Z]' $(MAKEFILE_LIST) | sort | awk -F ':.*?## ' 'NF==2 {printf "\033[36m  %-25s\033[0m %s\n", $$1, $$2}'

clean: clean-build clean-pyc clean-tests

clean-build: ## remove build artifacts
	rm -fr build/
	rm -fr dist/
	rm -fr *.egg-info

clean-pyc: ## remove Python file artifacts
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +

clean-tests: ## remove pytest artifacts
	rm -fr .pytest_cache/
	rm -fr htmlcov/
	rm -fr django-import-export/

test: ## run tests quickly with the default Python
	$(RUN_TEST_COMMAND)

messages: ## generate locale file translations
	cd import_export && django-admin makemessages -a && django-admin compilemessages && cd ..

coverage: ## generates codecov report
	coverage run tests/manage.py test core --settings=
	coverage combine
	coverage report

sdist: clean ## package
	python setup.py sdist
	ls -l dist

install-base-requirements: ## install package requirements
	pip install -r requirements/base.txt

install-test-requirements: ## install requirements for testing
	pip install -r requirements/test.txt

install-docs-requirements:  ## install requirements for docs
	pip install -r requirements/docs.txt

install-requirements: install-base-requirements install-test-requirements install-docs-requirements

build-html-doc: ## builds the project documentation in HTML format
	DJANGO_SETTINGS_MODULE=tests.settings make html -C docs
