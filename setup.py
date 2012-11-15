from setuptools import setup, find_packages
import os


VERSION = __import__("send_instance").__version__

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
]

setup(
    name="django-import-export",
    description="django-import-export",
    long_description=open(os.path.join(os.path.dirname(__file__),
        'README.rst')).read(),
    version=VERSION,
    author="Informatika Mihelac",
    author_email="bmihelac@mihelac.org",
    url="https://github.com/bmihelac/django-import-export",
    packages=find_packages(exclude=["tests"]),
)
