from setuptools import find_packages, setup


VERSION = __import__("import_export").__version__

CLASSIFIERS = [
    'Framework :: Django',
    'Framework :: Django :: 1.8',
    'Framework :: Django :: 1.9',
    'Framework :: Django :: 1.10',
    'Framework :: Django :: 1.11',
    'Framework :: Django :: 2.0',
    'Framework :: Django :: 2.1',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: BSD License',
    'Operating System :: OS Independent',
    'Programming Language :: Python',
    'Programming Language :: Python :: 2',
    'Programming Language :: Python :: 2.7',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.3',
    'Programming Language :: Python :: 3.4',
    'Programming Language :: Python :: 3.5',
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: 3.7',
    'Topic :: Software Development',
]

install_requires = [
    'diff-match-patch',
    'django>=1.8',
    'tablib',
]

setup(
    name="django-import-export",
    description="Django application and library for importing and exporting"
            "data with included admin integration.",
    version=VERSION,
    author="Informatika Mihelac",
    author_email="bmihelac@mihelac.org",
    license='BSD License',
    platforms=['OS Independent'],
    url="https://github.com/django-import-export/django-import-export",
    packages=find_packages(exclude=["tests"]),
    include_package_data=True,
    install_requires=install_requires,
    python_requires=">=2.7, !=3.0.*, !=3.1.*, !=3.2.*",
    classifiers=CLASSIFIERS,
    zip_safe=False,
)
