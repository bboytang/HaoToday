import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
DEBUG = False
ALLOWED_HOSTS = [h.strip() for h in os.environ["DJANGO_ALLOWED_HOSTS"].split(",") if h.strip()]

INSTALLED_APPS = [
    'discovery',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
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

ROOT_URLCONF = 'haotoday.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'haotoday.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {"default": {
    "ENGINE": "django.db.backends.postgresql",
    "NAME": os.environ["PGDATABASE"],
    "USER": os.environ["PGUSER"],
    "PASSWORD": os.environ["PGPASSWORD"],
    "HOST": os.environ["PGHOST"],
    "PORT": os.getenv("PGPORT", "5432"),
}}

# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

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


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'zh-hans'

TIME_ZONE = 'Asia/Shanghai'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'static/'

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "account"
# 内测部署由唯一暴露公网的 Caddy 设置转发协议，应用端口不对外发布。
if os.getenv("HAOTODAY_HTTPS") == "1":
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# 仅能由部署人员显式启用；没有真实 SMTP 时保持关闭。
EMAIL_HOST = os.getenv("HAOTODAY_SMTP_HOST", "")
EMAIL_PORT = int(os.getenv("HAOTODAY_SMTP_PORT", "465"))
EMAIL_USE_SSL = EMAIL_PORT == 465
EMAIL_USE_TLS = not EMAIL_USE_SSL
EMAIL_HOST_USER = os.getenv("HAOTODAY_SMTP_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("HAOTODAY_SMTP_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.getenv("HAOTODAY_FROM_EMAIL", "")
EMAIL_TIMEOUT = 10
ACCOUNT_ORIGIN = "https://8kraw.cloud"
ACCOUNT_MAIL_ENABLED = bool(EMAIL_HOST and DEFAULT_FROM_EMAIL and os.getenv("HAOTODAY_MAIL_ENABLED") == "1")
REGISTRATION_OPEN = ACCOUNT_MAIL_ENABLED and os.getenv("HAOTODAY_REGISTRATION_OPEN") == "1"
PASSWORD_RESET_TIMEOUT = 1800
