import os
import sys
from importlib.metadata import version

import django

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.append(os.path.abspath("."))
sys.path.append(os.path.abspath(".."))
sys.path.append(os.path.abspath("../tests"))
os.environ["DJANGO_SETTINGS_MODULE"] = "settings"

django.setup()

# -- General configuration -----------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.autosectionlabel",
]

autoclass_content = "both"

autosectionlabel_prefix_document = True

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# The suffix of source filenames.
source_suffix = ".rst"

# The master toctree document.
master_doc = "index"

# General information about the project.
project = "django-import-export"
copyright = "2012–2024, Bojan Mihelac and others."

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
release = version("django-import-export")
# for example take major/minor
version = ".".join(release.split(".")[:2])

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = "sphinx"

# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = "sphinx_rtd_theme"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

# Output file base name for HTML help builder.
htmlhelp_basename = "django-import-export"

# -- Options for LaTeX output --------------------------------------------------

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
    (
        "index",
        "django-import-export.tex",
        "django-import-export Documentation",
        "Bojan Mihelac",
        "manual",
    ),
]

# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    (
        "index",
        "django-import-export",
        "django-import-export Documentation",
        ["Bojan Mihelac"],
        1,
    )
]

# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    (
        "index",
        "django-import-export",
        "django-import-export Documentation",
        "Bojan Mihelac",
        "django-import-export",
        "Import/export data for Django",
        "Miscellaneous",
    ),
]

# Documents to append as an appendix to all manuals.
texinfo_appendices = []

# intersphinx documentation
intersphinx_mapping = {"tablib": ("https://tablib.readthedocs.io/en/stable/", None)}

exclude_patterns = ["image_src"]
