# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**django-import-export** is a Django application and library for importing and exporting data with admin integration. It supports multiple file formats (CSV, XLSX, JSON, etc.) via the `tablib` library and provides both programmatic and Django Admin UI interfaces for data import/export operations.

## Development Commands

### Testing
- **Run all tests**: `make test` or `PYTHONPATH=".:tests:${PYTHONPATH}" python -W error -m django test core --settings=settings`
- **Run tests in parallel**: `make testp`
- **Run tests with coverage**: `make coverage` or `coverage run tests/manage.py test core`
- **Run comprehensive tests (all databases)**: `./runtests.sh` (requires Docker for MySQL/PostgreSQL)
- **Run tests via tox**: `tox` (tests against multiple Python/Django combinations)

### Code Quality
- **Linting and formatting**: Pre-commit hooks handle this automatically via:
  - `black` (code formatting)
  - `isort` (import sorting)
  - `flake8` (linting)
  - `django-upgrade` (Django version compatibility)
  - `pyupgrade` (Python syntax modernization)
- **Run pre-commit manually**: `pre-commit run --all-files`
- **Max line length**: 88 characters (Black standard)

### Documentation
- **Build HTML docs**: `make build-html-doc`
  - First install docs requirements: `make install-docs-requirements` or `pip install -e .[docs]`
  - HTML output is generated in `docs/_build/html/`
  - Includes Sphinx documentation with RTD theme
- **Generate locale files**: `make messages`
- **Update documentation for releases**:
  - `docs/changelog.rst`: Add entries for new releases with format "X.Y.Z (unreleased)" or "X.Y.Z (YYYY-MM-DD)"
  - `docs/release_notes.rst`: Document breaking changes, deprecations, and migration guides
  - Follow existing format with bullet points, PR references like `(#XXXX <https://github.com/django-import-export/django-import-export/pull/XXXX>`_)
  - Include deprecation warnings with version numbers for when features will be removed

### Installation
- **Base requirements**: `make install-base-requirements` or `pip install .`
- **Test requirements**: `make install-test-requirements` or `pip install .[tests]`
- **Docs requirements**: `make install-docs-requirements` or `pip install .[docs]`

## Architecture Overview

### Core Components

**Resources (`resources.py`)**
- Central abstraction for data import/export operations
- `ModelResource`: Maps Django models to import/export operations
- Handles field mapping, data transformation, validation, and CRUD operations
- Supports customizable field definitions, widgets, and instance loading

**Fields (`fields.py`)**
- Maps between model attributes and export/import data representations
- Configurable with widgets for data transformation
- Supports readonly fields, default values, and custom attribute access

**Admin Integration (`admin.py`)**
- Mixins: `ImportExportMixinBase`, `BaseImportMixin`, `BaseExportMixin`
- Provides Django Admin UI for import/export operations
- Handles file uploads, preview functionality, and batch operations
- Integrates with Django's permission system

**Widgets (`widgets.py`)**
- Handle data type conversion and formatting
- Examples: `DateWidget`, `ForeignKeyWidget`, `ManyToManyWidget`
- Extensible for custom data transformation needs

**Formats (`formats/`)**
- Abstraction layer over `tablib` for different file formats
- Supports CSV, XLSX, JSON, YAML, and other formats
- Binary vs text format handling

### Key Patterns

**Declarative Configuration**
- Resources use Django-style declarative syntax similar to ModelAdmin
- Meta classes define model mappings, field selections, and options
- Field definitions support widgets, column names, and transformation logic

**Transaction Handling**
- Configurable transaction behavior via `IMPORT_EXPORT_USE_TRANSACTIONS`
- Supports atomic operations for data integrity
- Rollback capabilities on import errors

**Instance Loading**
- Pluggable instance loaders for different update strategies
- Default loaders handle create/update logic based on primary keys
- Custom loaders support business-specific lookup patterns

## Testing Structure

**Test Organization**
- Main tests in `tests/core/tests/`
- Test models in `tests/core/models.py` (Author, Book, Category, etc.)
- Settings in `tests/settings.py` with multi-database support
- Docker setup for MySQL/PostgreSQL testing via `tests/docker-compose.yml`

**Test Database Configuration**
- SQLite (default): Local file-based testing
- MySQL: Via Docker with `IMPORT_EXPORT_TEST_TYPE=mysql-innodb`
- PostgreSQL: Via Docker with `IMPORT_EXPORT_TEST_TYPE=postgres`
- Environment variables for database credentials in `runtests.sh`

## File Structure
- `import_export/`: Main package code
- `tests/`: Test suite with core app for testing
- `docs/`: Sphinx documentation
- `tox.ini`: Multi-environment testing configuration
- `pyproject.toml`: Project metadata and dependencies
- `Makefile`: Development command shortcuts