import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-local-development-only')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DJANGO_DEBUG', 'true').lower() == 'true'
if not DEBUG and not os.environ.get('DJANGO_SECRET_KEY'):
    raise ValueError('Set DJANGO_SECRET_KEY before running with debug disabled.')

ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1,testserver').split(',')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Custom project apps
    'accounts.apps.AccountsConfig',
    'authorities.apps.AuthoritiesConfig',
    'categories.apps.CategoriesConfig',
    'cases.apps.CasesConfig',
    'notifications.apps.NotificationsConfig',
    'audit.apps.AuditConfig',
    'dashboard.apps.DashboardConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'notifications.context_processors.unread_notifications',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database
# https://docs.djangoproject.com/en/6.1/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Custom User Model (Section 6 & Appendix A)
AUTH_USER_MODEL = 'accounts.User'

AUTHENTICATION_BACKENDS = [
    'accounts.backends.FacultyAuthBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# Password validation
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

# Internationalization - University of Sri Jayewardenepura (Sri Lanka)
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Colombo'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files (Images and video evidence uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# File upload limits (Section 5.1 & Section 12)
FILE_UPLOAD_MAX_MEMORY_SIZE = 25 * 1024 * 1024  # 25 MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 25 * 1024 * 1024

# Authentication URL Redirects
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'login'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Local email is printed to the console; configure SMTP for delivered email.
EMAIL_BACKEND = os.environ.get('DJANGO_EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.environ.get('EMAIL_HOST', '')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'true').lower() == 'true'
EMAIL_TIMEOUT = 10
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'fmsc@localhost')

MAX_VIDEO_DURATION_SECONDS = int(os.environ.get('MAX_VIDEO_DURATION_SECONDS', '120'))

# Public registration is restricted to configured university domains and subdomains.
UNIVERSITY_EMAIL_DOMAINS = [domain.strip().lower() for domain in os.environ.get('UNIVERSITY_EMAIL_DOMAINS', 'sjp.ac.lk').split(',') if domain.strip()]
EMAIL_VERIFICATION_TIMEOUT = 24 * 60 * 60

# Temporary verification preview is local-only and never enabled with real email delivery.
LOCAL_EMAIL_PREVIEW_ENABLED = (
    DEBUG
    and EMAIL_BACKEND == 'django.core.mail.backends.console.EmailBackend'
    and os.environ.get('LOCAL_EMAIL_PREVIEW_ENABLED', 'true').lower() == 'true'
)
