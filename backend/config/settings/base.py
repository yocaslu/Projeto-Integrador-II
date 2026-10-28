"""Configurações comuns a todos os ambientes.

Todos os valores sensíveis ou dependentes de ambiente vêm de variáveis de ambiente (RNF07).
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def env_list(nome: str, padrao: str = "") -> list[str]:
    """Lê uma variável de ambiente com valores separados por vírgula."""
    return [item.strip() for item in os.environ.get(nome, padrao).split(",") if item.strip()]


SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
DEBUG = False
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "django_filters",
    "drf_spectacular",
    "apps.localidades",
    "apps.catalogo",
    "apps.registros",
    "apps.importacao",
    "apps.api",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "anuario"),
        "USER": os.environ.get("POSTGRES_USER", "anuario"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        # JIT desligado: nas subconsultas de taxa, variação e participação, a compilação JIT
        # custava ~3 s e a execução ~0,3 s (ADR 0008; RNF02).
        "OPTIONS": {"options": "-c jit=off"},
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Diretórios das planilhas de origem e dos relatórios de validação (RF12)
DADOS_BRUTOS_DIR = Path(os.environ.get("DADOS_BRUTOS_DIR", BASE_DIR.parent / "dados" / "brutos"))
DADOS_RELATORIOS_DIR = Path(
    os.environ.get("DADOS_RELATORIOS_DIR", BASE_DIR.parent / "dados" / "relatorios")
)

REST_FRAMEWORK = {
    # A API pública é somente leitura (RNF06): não há autenticação nem permissões de escrita.
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "UNAUTHENTICATED_USER": None,
    "DEFAULT_VERSIONING_CLASS": "rest_framework.versioning.URLPathVersioning",
    "ALLOWED_VERSIONS": ["v1"],
    # Só vale fora de uma requisição (ex.: `manage.py spectacular`); toda rota traz a versão.
    "DEFAULT_VERSION": "v1",
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_PAGINATION_CLASS": "apps.api.paginacao.PaginacaoPorPagina",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "apps.api.erros.manipulador_problem_details",
    "COERCE_DECIMAL_TO_STRING": True,
    # formato=json|csv tem precedência sobre Accept; formato desconhecido → 406 (contrato, 5.1).
    "URL_FORMAT_OVERRIDE": "formato",
    "DEFAULT_CONTENT_NEGOTIATION_CLASS": "apps.api.negociacao.NegociacaoPorFormato",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "API do Anuário Brasileiro de Segurança Pública",
    "DESCRIPTION": (
        "Indicadores do Anuário Brasileiro de Segurança Pública 2026. "
        "Fontes: Fórum Brasileiro de Segurança Pública (FBSP) e IBGE."
    ),
    "VERSION": "1.0.0",
    "LICENSE": {"name": "AGPL-3.0", "url": "https://www.gnu.org/licenses/agpl-3.0.html"},
    "SERVE_INCLUDE_SCHEMA": False,
}
