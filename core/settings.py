from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# --- CONFIGURAÇÕES FACEBOOK ---
FACEBOOK_PIXEL_ID = "1463841368643880" 
FACEBOOK_ACCESS_TOKEN = "EAAK2xtj5h7YBQg2eYKFz9s14z2uXq5ap6pupIYpbw4f4ojBF2ST1QkujYZAlv14nrkHHqONqOaJv2oYebz1hkfhFZCWUxYdh0ZC27Bzc9sXX4VAAVa9V3DOsiI5INtHLpdzjiGsAem7nNXf1tMtqsai4T3KRmV7dMoSRVxH85rW0d5UYmurGxTQVRZAB8qoZAQgZDZD"

SECRET_KEY = 'django-insecure-3pn@rsa&a1#)u!v@#dd6)3ddm8vtx@wm=lh!8q@yv4nv(!4l1^'
DEBUG = True
ALLOWED_HOSTS = ['*', 'localhost', '127.0.0.1', '.ngrok-free.dev']
CSRF_TRUSTED_ORIGINS = ['https://gex-corp.up.railway.app']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Libs
    'rest_framework',
    'corsheaders',
    'django_filters',
    'drf_spectacular',
    
    # Apps
    'orders',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.AllowAny'],
    'DEFAULT_RENDERER_CLASSES': ('rest_framework.renderers.JSONRenderer',),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'GEX Corporation API',
    'DESCRIPTION': 'API de Integração Reportana (Read-Only)',
    'VERSION': '1.0.0',
    'SCHEMA_PATH_PREFIX': '/api/v1/',
}

CORS_ALLOW_ALL_ORIGINS = True
ROOT_URLCONF = 'core.urls'

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

WSGI_APPLICATION = 'core.wsgi.application'

# --- CONFIGURAÇÃO DO BANCO DE DADOS (SUPABASE POOLER) ---

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'postgres',
        
        # ATENÇÃO: Usuário do Pooler tem o ID do projeto no final
        'USER': 'postgres.bglmcehgzohkmeqnhjtw', 
        
        'PASSWORD': 'Denis5197148.',
        
        # ATENÇÃO: Host IPv4 do Pooler (não use db.bglm...)
        'HOST': 'aws-1-us-east-1.pooler.supabase.com',
        
        # ATENÇÃO: Porta do Pooler
        'PORT': '5432',
    }
}

# Removemos o DATABASE_ROUTERS pois só temos 1 banco agora
# DATABASE_ROUTERS = ['core.db_router.EmpresaRouter']

AUTH_PASSWORD_VALIDATORS = [{'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},]
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True
STATIC_URL = 'static/'