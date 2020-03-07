import os

from setuptools import find_packages, setup

VERSION = __import__("import_export").__version__

CLASSIFIERS = [
    'Framework :: Django',
    'Framework :: Django :: 2.0',
    'Framework :: Django :: 2.1',
    'Framework :: Django :: 2.2',
    'Framework :: Django :: 3.0',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: BSD License',
    'Operating System :: OS Independent',
    'Programming Language :: Python',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.5',
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: 3.7',
    'Programming Language :: Python :: 3 :: Only',
    'Topic :: Software Development',
]

install_requires = [
    'diff-match-patch',
    'Django>=2.0',
    'tablib[html,ods,xls,xlsx,yaml]>=0.14.0',
]


with open(os.path.join(os.path.dirname(__file__), 'README.rst')) as f:
    readme = f.read()


setup(
    name="django-import-export",
    description="Django application and library for importing and exporting"
                " data with included admin integration.",
    long_description=readme,
    version=VERSION,
    author="Informatika Mihelac",
    author_email="bmihelac@mihelac.org",
    license='BSD License',
    platforms=['OS Independent'],
    url="https://github.com/django-import-export/django-import-export",
    packages=find_packages(exclude=["tests"]),
    include_package_data=True,
    install_requires=install_requires,
    python_requires=">=3.5",
    classifiers=CLASSIFIERS,
    zip_safe=False,
)
