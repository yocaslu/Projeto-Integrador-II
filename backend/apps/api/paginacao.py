"""Paginação por número de página para /registros/ e /populacao/.

Os catálogos e as consultas agregadas (regiões, estados, indicadores, fontes, recortes,
ranking, comparação e metadados) não são paginados: nessas views, use pagination_class = None.
"""

from rest_framework.pagination import PageNumberPagination


class PaginacaoPorPagina(PageNumberPagination):
    page_size = 100
    page_query_param = "pagina"
    page_size_query_param = "tamanho"
    max_page_size = 1000
