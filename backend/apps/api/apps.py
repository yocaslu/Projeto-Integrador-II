from django.apps import AppConfig


class ApiConfig(AppConfig):
    """Camada HTTP da API pública, somente leitura (RNF06)."""

    name = "apps.api"
    verbose_name = "API"
