"""
Django settings for Santana Afiliados Bot.
Especificação V1.2 - 04/11/2026
"""

from pathlib import Path
import os
import sys
from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured

# Carrega arquivo .env da raiz do projeto ou diretório local
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR.parent / '.env', override=True)
load_dotenv(BASE_DIR / '.env', override=True)

# Adiciona o diretório 'apps' ao sys.path
APPS_DIR = BASE_DIR / 'apps'
if str(APPS_DIR) not in sys.path:
    sys.path.insert(0, str(APPS_DIR))

SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    raise ImproperlyConfigured('Set SECRET_KEY in the project .env file.')

DEBUG = os.getenv('DEBUG', 'True').lower() in ('true', '1', 'yes')

ALLOWED_HOSTS = [host.strip() for host in os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1,0.0.0.0,backend').split(',')]

# Aplicações instaladas
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Terceiros
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',

    # Santana Afiliados Bot Apps (V1.2)
    'apps.catalog',
    'apps.integrations.mercadolivre',
    'apps.automation',
    'apps.affiliates',
    'apps.campaigns',
    'apps.publications',
    'apps.analytics',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
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
ASGI_APPLICATION = 'config.asgi.application'

# Configuração de Banco de Dados (PostgreSQL 16 Nativo / Docker)
USE_SQLITE = os.getenv('USE_SQLITE', 'False').lower() in ('true', '1', 'yes')

if USE_SQLITE:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': os.getenv('DB_ENGINE', 'django.db.backends.postgresql'),
            'NAME': os.getenv('DB_NAME', 'santana_afiliados_db'),
            'USER': os.getenv('DB_USER', 'santana_admin'),
            'PASSWORD': os.getenv('DB_PASSWORD', ''),
            'HOST': os.getenv('DB_HOST', 'localhost'),
            'PORT': os.getenv('DB_PORT', '5432'),
        }
    }

# Validações de Senha
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internacionalização
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Django REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.AllowAny',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# Configurações de CORS
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOWED_ORIGINS = [
    origin.strip() for origin in os.getenv(
        'CORS_ALLOWED_ORIGINS',
        'http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173'
    ).split(',') if origin.strip()
]

# Celery & Redis (Seção 11.3)
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True

# Importa agendamentos do Celery Beat
try:
    from apps.automation.schedules import AUTOMATION_BEAT_SCHEDULE
    CELERY_BEAT_SCHEDULE = AUTOMATION_BEAT_SCHEDULE
except ImportError:
    CELERY_BEAT_SCHEDULE = {}

# Configurações Mercado Livre
MERCADOLIVRE_API_URL = os.getenv('MERCADOLIVRE_API_URL', 'https://api.mercadolibre.com')
MERCADOLIVRE_SITE_ID = os.getenv('MERCADOLIVRE_SITE_ID', 'MLB')
MERCADOLIVRE_CLIENT_ID = os.getenv('MERCADOLIVRE_CLIENT_ID', '')
MERCADOLIVRE_CLIENT_SECRET = os.getenv('MERCADOLIVRE_CLIENT_SECRET', '')
MERCADOLIVRE_ACCESS_TOKEN = os.getenv('MERCADOLIVRE_ACCESS_TOKEN', '')

# Configurações de Envio WhatsApp (Evolution API / Z-API / Webhook)
WHATSAPP_API_ENABLED = os.getenv('WHATSAPP_API_ENABLED', 'False').lower() in ('true', '1', 'yes')
WHATSAPP_API_URL = os.getenv('WHATSAPP_API_URL', '')
WHATSAPP_API_TOKEN = os.getenv('WHATSAPP_API_TOKEN', '')
WHATSAPP_GROUP_ID = os.getenv('WHATSAPP_GROUP_ID', '')
WHATSAPP_GATEWAY_TYPE = os.getenv('WHATSAPP_GATEWAY_TYPE', 'evolution').lower()

# Termos de Pesquisa Iniciais por Categoria (Especificação V1.2 - Seção 6.2)
SEARCH_TERMS = {
    "technology": [
        "controle xbox",
        "fone bluetooth",
        "acessorios gamer",
        "smartwatch",
    ],
    "fashion": [
        "tenis masculino",
        "camiseta masculina",
        "bermuda masculina",
    ],
    "home": [
        "organizador domestico",
        "utensilios cozinha",
        "ferramentas",
    ],
    "beauty": [
        "perfume masculino",
        "cuidados pessoais",
        "maquina de cortar cabelo",
    ],
}

# Pesos de Pontuação de Oportunidade (Especificação V1.2 - Seção 8.1)
OPPORTUNITY_SCORE_WEIGHTS = {
    "price_within_budget": 20,   # Preço até R$ 200
    "seller_reputation": 20,     # Reputação verde
    "product_new_and_active": 15,# Novo e ativo
    "price_competitiveness": 20, # Desconto verificável
    "commission_confirmed": 15,  # Comissão cadastrada e confirmada
    "commercial_attractiveness": 10, # Atratividade comercial
}
BUDGET_MAX_PREFERENTIAL = float(os.getenv('BUDGET_MAX_PREFERENTIAL', '200.00'))
PRICE_ALERT_THRESHOLD_PERCENT = float(os.getenv('PRICE_ALERT_THRESHOLD_PERCENT', '5.0'))
