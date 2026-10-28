"""Cache HTTP das respostas (RNF11; contrato, seção 7).

Como os dados só mudam em uma nova importação, toda resposta 200 de um recurso de dados (JSON e
CSV) leva:

- `Cache-Control: public, max-age=86400`;
- `ETag: W/"<versao da carga>-<json|csv>"`: muda com uma nova importação e difere entre as duas
  representações da mesma URL;
- `Vary: Accept`, porque a mesma URL serve JSON e CSV.

`If-None-Match` com o ETag atual → 304, sem corpo, com os mesmos cabeçalhos de cache. A
comparação é fraca (RFC 9110, 13.1.2): `W/"x"` e `"x"` casam. A resposta é montada antes, para que
uma requisição inválida receba o 400, e não um 304; no CSV, o streaming nem começa.

Erros não passam por aqui e não levam `Cache-Control: public`; sem carga concluída, o 503 sai com
`no-store` e sem ETag (seção 7.1, `apps/api/erros.py`).
"""

from django.http import HttpResponseNotModified
from django.utils.cache import patch_vary_headers
from django.utils.http import parse_etags

MAX_AGE = 86_400
CACHE_CONTROL = f"public, max-age={MAX_AGE}"
CABECALHOS_DO_304 = ("Cache-Control", "ETag", "Vary")


def etag(versao: str, formato: str) -> str:
    return f'W/"{versao}-{formato}"'


def _opaca(etag_: str) -> str:
    return etag_.removeprefix("W/")


def casa(if_none_match: str | None, atual: str) -> bool:
    """Comparação fraca entre o `If-None-Match` do cliente e o ETag atual (inclusive `*`)."""
    if not if_none_match:
        return False
    pedidos = parse_etags(if_none_match)
    return "*" in pedidos or _opaca(atual) in {_opaca(pedido) for pedido in pedidos}


def aplicar(request, resposta, versao: str, formato: str):
    """Cabeçalhos de cache numa resposta 200; com o ETag atual em `If-None-Match`, 304."""
    atual = etag(versao, formato)
    resposta["Cache-Control"] = CACHE_CONTROL
    resposta["ETag"] = atual
    patch_vary_headers(resposta, ["Accept"])
    if not casa(request.headers.get("If-None-Match"), atual):
        return resposta
    nao_modificada = HttpResponseNotModified()
    for nome in CABECALHOS_DO_304:
        nao_modificada[nome] = resposta[nome]
    return nao_modificada
