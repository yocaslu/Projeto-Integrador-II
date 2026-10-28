"""Paginação por número de página para /registros/ e /populacao/ (contrato, seção 4).

Os catálogos e as consultas agregadas não são paginados. Diferente do PageNumberPagination do DRF,
que corta `tamanho` em silêncio e devolve 404 para página inexistente, aqui `tamanho` acima de
1000 e página além da última são 400 (contrato, seção 6). `pagina` e `tamanho` já chegam
validados por `LeitorParametros.paginacao()`.

A resposta é o envelope `{"count", "next", "previous", "results"}`, com `next` e `previous` em URL
absoluta que preserva os demais parâmetros. Como os dados só mudam numa nova importação, a ordem
total (critério, ordem padrão, `id`) basta para que um registro não troque de página.
"""

from math import ceil

from django.db.models import QuerySet
from rest_framework.exceptions import ValidationError
from rest_framework.utils.urls import remove_query_param, replace_query_param

from apps.api.v1.parametros import PAGINA, Paginacao


def paginar(request, consulta: QuerySet, total: int, paginacao: Paginacao) -> tuple[list, dict]:
    """Itens da página e o envelope sem `results`; página além da última → 400.

    `total` vem de quem chama, para que a contagem rode sobre a consulta filtrada sem as anotações.
    Sem nenhum item, a página 1 existe e vem vazia.
    """
    paginas = max(1, ceil(total / paginacao.tamanho))
    if paginacao.pagina > paginas:
        raise ValidationError({PAGINA: [f"Página {paginacao.pagina} além da última ({paginas})."]})
    inicio = (paginacao.pagina - 1) * paginacao.tamanho
    itens = list(consulta[inicio : inicio + paginacao.tamanho])

    url = request.build_absolute_uri()
    proxima = (
        replace_query_param(url, PAGINA, paginacao.pagina + 1)
        if paginacao.pagina < paginas
        else None
    )
    if paginacao.pagina == 1:
        anterior = None
    elif paginacao.pagina == 2:
        anterior = remove_query_param(url, PAGINA)
    else:
        anterior = replace_query_param(url, PAGINA, paginacao.pagina - 1)
    return itens, {"count": total, "next": proxima, "previous": anterior}
