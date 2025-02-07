.PHONY: clean-pyc clean-build docs help
.PHONY: lint test coverage test-codecov
.DEFAULT_GOAL := help
RUN_TEST_COMMAND=PYTHONPATH=".:tests:${PYTHONPATH}" python -W error -m django test core --settings=settings
help:
	@grep '^[a-zA-Z]' $(MAKEFILE_LIST) | sort | awk -F ':.*?## ' 'NF==2 {printf "\033[36m  %-25s\033[0m %s\n", $$1, $$2}'

clean: clean-build clean-pyc clean-tests

clean-build: ## remove build artifacts
	rm -fr build/
	rm -fr dist/
	rm -fr *.egg-info
	rm -f import_export/_version.py
	rm -fr .coverage.*

clean-pyc: ## remove Python file artifacts
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +

clean-tests: ## remove pytest artifacts
	rm -fr .pytest_cache/
	rm -fr htmlcov/
	rm -fr django-import-export/

test: ## run tests with the default Python
	$(RUN_TEST_COMMAND)

testp: ## run tests in parallel with the default Python
	$(RUN_TEST_COMMAND) --parallel

messages: ## generate locale file translations
	cd import_export && django-admin makemessages -a && django-admin compilemessages && cd ..

coverage: ## generates codecov report
	coverage run tests/manage.py test core
	coverage combine
	coverage report

sdist: clean ## package
	python setup.py sdist
	ls -l dist

install-base-requirements: ## install package requirements
	pip install .

install-test-requirements: ## install requirements for testing
	pip install .[tests]

install-docs-requirements:  ## install requirements for docs
	pip install --editable .[docs]

install-requirements: install-base-requirements install-test-requirements install-docs-requirements

## builds the project documentation in HTML format
## run `pip install -e .` first if running locally
build-html-doc:
	DJANGO_SETTINGS_MODULE=tests.settings make html -C docs
