from __future__ import unicode_literals

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
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

# For backwards compatibility for Django 1.8
MIDDLEWARE_CLASSES = MIDDLEWARE

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': (
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ),
        },
    },
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'database.db',
    }
}
