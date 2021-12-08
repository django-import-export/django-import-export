import os
import sys

import django

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.sites',

    'import_export',

    'core',
]

SITE_ID = 1

ROOT_URLCONF = "urls"

DEBUG = True

STATIC_URL = '/static/'

SECRET_KEY = '2n6)=vnp8@bu0om9d05vwf7@=5vpn%)97-!d*t4zq1mku%0-@j'

MIDDLEWARE = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': (
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.request',
            ),
        },
    },
]

if django.VERSION >= (3, 2):
    DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

if os.environ.get('IMPORT_EXPORT_TEST_TYPE') == 'mysql-innodb':
    IMPORT_EXPORT_USE_TRANSACTIONS = True
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'import_export',
            'USER': os.environ.get('IMPORT_EXPORT_MYSQL_USER', 'root'),
            'PASSWORD': os.environ.get('IMPORT_EXPORT_MYSQL_PASSWORD', 'password'),
            'HOST': '127.0.0.1',
            'PORT': 3306,
            'TEST': {
                'CHARSET': 'utf8',
                'COLLATION': 'utf8_general_ci',
            }
        }
    }


elif os.environ.get('IMPORT_EXPORT_TEST_TYPE') == 'postgres':
    IMPORT_EXPORT_USE_TRANSACTIONS = True
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': 'import_export',
            'USER': os.environ.get('IMPORT_EXPORT_POSTGRESQL_USER'),
            'PASSWORD': os.environ.get('IMPORT_EXPORT_POSTGRESQL_PASSWORD'),
            'HOST': 'localhost',
            'PORT': 5432
        }
    }
else:
    if 'test' in sys.argv:
        database_name = ''
    else:
        database_name = os.path.join(os.path.dirname(__file__), 'database.db')
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': database_name,
        }
    }

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'handlers': {
        'console': {
            'class': 'logging.NullHandler'
        }
    },
    'root': {
        'handlers': ['console'],
    }}


USE_TZ = False
