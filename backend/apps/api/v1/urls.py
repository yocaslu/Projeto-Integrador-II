"""Rotas da versão 1 da API, sob /api/v1/ (contrato, seção 4)."""

from django.urls import path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from apps.api.v1 import views

urlpatterns = [
    path("regioes/", views.ListaRegioes.as_view(), name="regioes"),
    path("regioes/<str:sigla>/", views.DetalheRegiao.as_view(), name="regiao"),
    path("estados/", views.ListaEstados.as_view(), name="estados"),
    path("estados/<str:uf>/", views.DetalheEstado.as_view(), name="estado"),
    path("indicadores/", views.ListaIndicadores.as_view(), name="indicadores"),
    path("indicadores/<slug:slug>/", views.DetalheIndicador.as_view(), name="indicador"),
    path("recortes/", views.ListaRecortes.as_view(), name="recortes"),
    path("fontes/", views.ListaFontes.as_view(), name="fontes"),
    path("populacao/", views.ListaPopulacao.as_view(), name="populacao"),
    path("registros/", views.ListaRegistros.as_view(), name="registros"),
    path("registros/<int:id>/", views.DetalheRegistro.as_view(), name="registro"),
    # A implementar: ranking, comparacao e metadados.
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    path("redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]
