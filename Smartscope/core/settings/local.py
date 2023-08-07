"""
Initialise environment variables for local only
"""
import os
# from django.core.files.storage import FileSystemStorage

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
SETTINGS_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(SETTINGS_DIR))
PROJECT_DIR = os.path.dirname(BASE_DIR)

BUILD_DIR = os.path.dirname(PROJECT_DIR)
os.environ.setdefault('DEFAULT_UMASK', '002')
os.environ.setdefault('FORCE_CPU', 'True')
os.environ.setdefault('CONFIG', \
    os.path.join(BUILD_DIR, "config/smartscope/"))
os.environ.setdefault('EXTERNAL_PLUGINS_DIRECTORY', \
    os.path.join(BUILD_DIR, 'external_plugins'))
os.environ.setdefault('TEST_FILES', os.path.join(BUILD_DIR, \
    'data', 'smartscope', 'smartscope_testfiles'))
os.environ.setdefault('IMOD_DIR', '/usr/local/IMOD')
os.environ.setdefault('CTFFIND',os.path.join(BUILD_DIR, \
    'SmartScope', 'config', 'singularity', 'ctffind'))


AUTOSCREENDIR = os.getenv('AUTOSCREENDIR',\
    os.path.join(BUILD_DIR, 'data', 'smartscope'))
TEMPDIR = os.getenv('TEMPDIR', os.path.join(BUILD_DIR, 'temp'))


SECRET_KEY = os.getenv('SECRET_KEY', 'dev')
DEBUG = eval(os.getenv('DEBUG', 'True'))
DEPLOY = eval(os.getenv('DEPLOY', 'False'))


ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost').split(',')
CSRF_TRUSTED_ORIGINS = [f'https://*.{host}' for host in ALLOWED_HOSTS]

APP = os.getenv('APP')
# Application definition
# Storage locations
USE_STORAGE = eval(os.getenv('USE_STORAGE', 'True'))
USE_LONGTERMSTORAGE = eval(os.getenv('USE_LONGTERMSTORAGE', 'True'))
USE_AWS = eval(os.getenv('USE_AWS', 'False'))
USE_MICROSCOPE = eval(os.getenv('USE_MICROSCOPE', 'True'))
AUTOSCREENSTORAGE = os.getenv('AUTOSCREENSTORAGE', \
    os.path.join(BUILD_DIR, 'data', 'smartscope'))

INSTALLED_APPS = [
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken',
    'django_filters',
    'storages',
    'channels',
    'Smartscope.core.settings.apps.Frontend',
    'Smartscope.core.settings.apps.API',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.common.CommonMiddleware',
]

ROOT_URLCONF = 'Smartscope.server.main.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'server/main/custom_templates'),
            os.path.join(BASE_DIR, 'server/main/templates')
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'Smartscope.server.frontend.context_processors.base_settings',
            ],
        },
    },
]

WSGI_APPLICATION = 'Smartscope.server.main.wsgi.application'
ASGI_APPLICATION = 'Smartscope.server.main.asgi.application'

# Database
# https://docs.djangoproject.com/en/3.0/ref/settings/#databases

REDIS_HOST=os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT=os.getenv('REDIS_PORT', 6379)
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [REDIS_HOST, REDIS_PORT],
        },
    },
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': f"redis://{REDIS_HOST}:{REDIS_PORT}",
    }
}


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv('MYSQL_DATABASE', 'smartscope'),
        'HOST': os.environ.get("MYSQL_HOST", '127.0.0.1'),
        'PORT': os.getenv('MYSQL_PORT', 3306),
        'USER': os.getenv('MYSQL_USER', 'dev'),
        'PASSWORD': os.getenv('MYSQL_PASSWORD', 'dev'),
        'CONN_MAX_AGE': 0,
        'OPTIONS': {
            'unix_socket': '/run/mysqld/mysqld.sock',
        }
    }
}


# Password validation
# https://docs.djangoproject.com/en/3.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'Smartscope.server.api.pagination.StandardResultsSetPagination',
    'PAGE_SIZE': 10,
    'DEFAULT_FILTER_BACKENDS': ('django_filters.rest_framework.DjangoFilterBackend',),
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
        'rest_framework_yaml.renderers.YAMLRenderer'
    ],
}



LANGUAGE_CODE = 'en-us'

TIME_ZONE = os.getenv('TIMEZONE', 'America/New_York')

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'

STATICFILES_DIRS = [
    os.path.join(PROJECT_DIR, "static"),
]

LOGIN_REDIRECT_URL = '/smartscope'
LOGOUT_REDIRECT_URL = '/login'
LOGIN_URL = '/login'
