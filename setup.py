from setuptools import setup, find_packages


VERSION = __import__("import_export").__version__

CLASSIFIERS = [
    'Framework :: Django',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: BSD License',
    'Operating System :: OS Independent',
    'Topic :: Software Development',
]

install_requires = [
    'tablib',
    'Django>=1.4.2',
    'diff-match-patch',
]

setup(
    name="django-import-export",
    description="Django application and library for importing and exporting"
            "data with included admin integration.",
    version=VERSION,
    author="Informatika Mihelac",
    author_email="bmihelac@mihelac.org",
    url="https://github.com/bmihelac/django-import-export",
    packages=find_packages(exclude=["tests"]),
    package_data={'import_export': ['templates/admin/import_export/*.html']},
    install_requires=install_requires,
)
