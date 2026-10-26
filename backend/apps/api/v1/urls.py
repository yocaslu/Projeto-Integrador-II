"""Rotas da versão 1 da API, sob /api/v1/."""

from django.urls import path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    # Recursos a implementar: regioes, estados, indicadores, recortes, fontes, populacao,
    # registros, ranking, comparacao e metadados (ver o contrato da API no roteiro).
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    path("redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]
