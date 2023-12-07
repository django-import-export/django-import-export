import os

from setuptools import find_packages, setup

VERSION = __import__("import_export").__version__

CLASSIFIERS = [
    "Framework :: Django",
    "Framework :: Django :: 3.2",
    "Framework :: Django :: 4.1",
    "Framework :: Django :: 4.2",
    "Framework :: Django :: 5.0",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: BSD License",
    "Operating System :: OS Independent",
    "Programming Language :: Python",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3 :: Only",
    "Topic :: Software Development",
]

# tablib temporarily pinned to 3.5.0 - see issue #1602
install_requires = [
    "diff-match-patch",
    "Django>=3.2",
    "tablib[html,ods,xls,xlsx,yaml]==3.5.0",
]


with open(os.path.join(os.path.dirname(__file__), "README.rst")) as f:
    readme = f.read()


setup(
    name="django-import-export",
    description="Django application and library for importing and exporting"
    " data with included admin integration.",
    long_description=readme,
    version=VERSION,
    author="Bojan Mihelač",
    author_email="djangoimportexport@gmail.com",
    maintainer="Matthew Hegarty",
    maintainer_email="djangoimportexport@gmail.com",
    license="BSD License",
    platforms=["OS Independent"],
    url="https://github.com/django-import-export/django-import-export",
    project_urls={
        "Documentation": "https://django-import-export.readthedocs.io/en/stable/",
        "Changelog": "https://django-import-export.readthedocs.io/en/stable/changelog.html",  # noqa: E501
    },
    packages=find_packages(exclude=["tests"]),
    include_package_data=True,
    install_requires=install_requires,
    python_requires=">=3.8",
    classifiers=CLASSIFIERS,
    zip_safe=False,
)
