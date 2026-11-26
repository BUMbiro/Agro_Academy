import os
import sys
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_env_file(path):
    """Простой парсер .env: читает KEY=VALUE и выставляет в os.environ."""
    if not path.exists():
        return
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, _, value = line.partition('=')
            os.environ.setdefault(key.strip(), value.strip())


# Загружаем переменные из .env
_load_env_file(BASE_DIR / '.env')

SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-your-secret-key')

DEBUG = os.getenv('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # DRF
    'rest_framework',
    'rest_framework_simplejwt',
    # Фильтрация
    'django_filters',
    # Документация API (OpenAPI 3)
    'drf_spectacular',
    # Локальные приложения
    'users',
    'materials',
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
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'agro_academy'),
        'USER': os.getenv('DB_USER', 'agro_academy_user'),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
        'OPTIONS': {
            'connect_timeout': 5,
        },
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'ru-ru'
TIME_ZONE = 'Europe/Moscow'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ============================================================
# Django REST Framework
# ============================================================

REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.OrderingFilter',
    ],
    # Генерация OpenAPI-схемы
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    # Лимит на создание платёжных сессий (рекомендация Stripe)
    'DEFAULT_THROTTLE_RATES': {
        'payments_checkout': '10/minute',
    },
}

# ============================================================
# Документация API (drf-spectacular)
# ============================================================

SPECTACULAR_SETTINGS = {
    'TITLE': 'AgroAcademy API',
    'DESCRIPTION': (
        'REST API образовательной платформы **«Фермерская академия»**: курсы и уроки '
        'для фермеров и агробизнеса, подписки, платежи и онлайн-оплата через **Stripe**.\n\n'
        '### Авторизация\n'
        '1. Получите токены: `POST /api/token/` (email + пароль).\n'
        '2. Нажмите **Authorize** и вставьте `access`-токен (без слова Bearer).\n\n'
        '### Онлайн-оплата\n'
        '`POST /api/payments/checkout/` → перейдите по `payment_link` → оплатите тестовой картой '
        '`4242 4242 4242 4242` → проверьте статус `GET /api/payments/{id}/status/`.'
    ),
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    # Отдельные схемы для запроса и ответа (корректные read_only / write_only и загрузка файлов)
    'COMPONENT_SPLIT_REQUEST': True,
    'SCHEMA_PATH_PREFIX': r'/api/',
    'SWAGGER_UI_SETTINGS': {
        'persistAuthorization': True,  # токен не сбрасывается после перезагрузки страницы
        'docExpansion': 'none',
        'filter': True,
    },
    'TAGS': [
        {'name': 'Авторизация', 'description': 'Получение и обновление JWT-токенов.'},
        {'name': 'Пользователи', 'description': 'Регистрация и профили.'},
        {'name': 'Курсы', 'description': 'CRUD курсов. Владелец видит свои, модератор — все.'},
        {'name': 'Подписки', 'description': 'Подписка на обновления курса.'},
        {'name': 'Уроки', 'description': 'CRUD уроков (Generic-классы).'},
        {'name': 'Платежи', 'description': 'История платежей и онлайн-оплата через Stripe.'},
    ],
    # Единые имена enum-ов в схеме (без предупреждений о коллизиях)
    'ENUM_NAME_OVERRIDES': {
        'PaymentMethodEnum': 'users.models.Payment.PaymentMethod',
        'PaymentStatusEnum': 'users.models.Payment.Status',
    },
}

# ============================================================
# JWT (SimpleJWT)
# ============================================================

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# ============================================================
# Stripe
# ============================================================

STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY', '')
STRIPE_CURRENCY = os.getenv('STRIPE_CURRENCY', 'rub').lower()
STRIPE_MIN_AMOUNT = Decimal(os.getenv('STRIPE_MIN_AMOUNT', '50'))
# Пусто = строятся автоматически от адреса запроса
STRIPE_SUCCESS_URL = os.getenv('STRIPE_SUCCESS_URL', '')
STRIPE_CANCEL_URL = os.getenv('STRIPE_CANCEL_URL', '')

# ============================================================
# Кастомная модель пользователя
# ============================================================

AUTH_USER_MODEL = 'users.User'

# В тестах не тратим время на медленное хеширование паролей
if 'test' in sys.argv:
    PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
