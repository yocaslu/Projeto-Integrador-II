"""Exportação em CSV (RF07; contrato, seção 5).

- Em /registros/, /populacao/, /ranking/ e /comparacao/, por `formato=csv` ou `Accept: text/csv`;
  nos demais recursos, 406 (eles não declaram este renderizador).
- Filtros, validação e ordenação são os da versão JSON; erro sai sempre em JSON (regra 27).
- Sem paginação: a exportação é completa, limitada a 50 mil linhas, contadas antes do streaming.
- RFC 4180 (`,`, aspas só quando necessário, `\\r\\n`), UTF-8 sem BOM, cabeçalho sempre presente,
  nenhuma linha de comentário, nulo = campo vazio.
- Cada linha sai dos mesmos serializers do JSON, achatada pelas regras da seção 5.3: os números
  têm os mesmos formatos e arredondamentos (seção 1.2), e `fonte`/`taxa_fonte` vêm em toda linha
  (RF11, RNF12). A lista e a ordem das colunas são contrato (regra 22).
"""

import csv
from collections.abc import Iterable, Iterator

from django.http import StreamingHttpResponse
from rest_framework.exceptions import ValidationError
from rest_framework.renderers import BaseRenderer

LIMITE_LINHAS_CSV = 50_000
TIPO_CSV = "text/csv; charset=utf-8; header=present"


class RenderizadorCSV(BaseRenderer):
    """Só seleciona o formato na negociação: a resposta CSV é montada por `resposta_csv`."""

    media_type = "text/csv"
    format = "csv"
    charset = "utf-8"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        raise NotImplementedError("Respostas CSV são enviadas por resposta_csv (streaming).")


_CONTEXTO_DO_INDICADOR = ["indicador_slug", "indicador_nome", "unidade"]
_RECORTE = ["recorte_id", "recorte_rotulo"]
_LOCALIDADE = [
    "localidade_nivel",
    "localidade_codigo",
    "localidade_codigo_ibge",
    "localidade_nome",
]
_VALORES = [
    "valor",
    "situacao",
    "metodo",
    "taxa_valor",
    "taxa_base",
    "taxa_origem",
    "taxa_fonte",
]
_VARIACAO_E_PARTICIPACAO = [
    "variacao_ano_referencia",
    "variacao_valor_pct",
    "variacao_taxa_pct",
    "participacao_tipo",
    "participacao_indicador",
    "participacao_valor_pct",
    "fonte",
    "observacao",
]

COLUNAS = {
    "registros": [
        "id",
        "ano",
        *_LOCALIDADE,
        "indicador_slug",
        "indicador_nome",
        *_RECORTE,
        "unidade",
        *_VALORES,
        "taxa_publicada",
        *_VARIACAO_E_PARTICIPACAO,
    ],
    "populacao": ["id", "ano", *_LOCALIDADE, "valor", "fonte"],
    "ranking": [
        "ano",
        *_CONTEXTO_DO_INDICADOR,
        "criterio",
        *_RECORTE,
        "posicao",
        *_LOCALIDADE,
        *_VALORES,
        *_VARIACAO_E_PARTICIPACAO,
    ],
    "comparacao": [
        *_CONTEXTO_DO_INDICADOR,
        *_RECORTE,
        *_LOCALIDADE,
        "ano",
        *_VALORES,
        *_VARIACAO_E_PARTICIPACAO,
    ],
}
"""Colunas de cada recurso, na ordem da seção 5.3 do contrato."""


def achatar(item: dict, prefixo: str = "") -> dict:
    """Objeto do JSON → colunas unidas por `_` (contrato, 5.3).

    Exceções: `fonte` (e `taxa.fonte`) viram só o nome; `recorte` vira `recorte_id` e
    `recorte_rotulo`, sem os itens; `participacao.referencia` vira `participacao_tipo` e
    `participacao_indicador`. Listas (como os itens do recorte) não entram.
    """
    colunas: dict = {}
    for chave, valor in item.items():
        nome = f"{prefixo}{chave}"
        if chave == "fonte":
            colunas[nome] = valor["nome"] if valor else None
        elif chave == "recorte":
            colunas[f"{prefixo}recorte_id"] = valor["id"] if valor else None
            colunas[f"{prefixo}recorte_rotulo"] = valor["rotulo"] if valor else None
        elif chave == "referencia":
            colunas[f"{prefixo}tipo"] = valor["tipo"] if valor else None
            colunas[f"{prefixo}indicador"] = valor["indicador"] if valor else None
        elif isinstance(valor, dict):
            colunas |= achatar(valor, f"{nome}_")
        elif not isinstance(valor, list):
            colunas[nome] = valor
    return colunas


def verificar_limite(total: int, limite: int | None = None) -> None:
    """Acima do limite → 400, antes de começar o streaming (contrato, 5.1)."""
    limite = LIMITE_LINHAS_CSV if limite is None else limite
    if total > limite:
        raise ValidationError(
            {
                "formato": [
                    f"A exportação teria {total} linhas; o limite é {limite}. "
                    "Restrinja com ano, uf ou indicador."
                ]
            }
        )


class _Eco:
    """Pseudo-arquivo para o csv.writer: devolve a linha formatada em vez de gravá-la."""

    def write(self, valor: str) -> str:
        return valor


def _linhas(recurso: str, itens: Iterable[dict]) -> Iterator[bytes]:
    colunas = COLUNAS[recurso]
    escritor = csv.writer(_Eco(), lineterminator="\r\n")
    yield escritor.writerow(colunas).encode("utf-8")
    for item in itens:
        achatado = achatar(item)
        yield escritor.writerow(
            ["" if achatado.get(coluna) is None else achatado[coluna] for coluna in colunas]
        ).encode("utf-8")


def resposta_csv(recurso: str, itens: Iterable[dict]) -> StreamingHttpResponse:
    """Resposta por streaming; `itens` são objetos do JSON (de preferência, um gerador)."""
    resposta = StreamingHttpResponse(_linhas(recurso, itens), content_type=TIPO_CSV)
    resposta["Content-Disposition"] = f'attachment; filename="anuario-{recurso}.csv"'
    return resposta
