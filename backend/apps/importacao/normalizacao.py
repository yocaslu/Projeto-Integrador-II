"""Normalização das células da planilha do FBSP.

A planilha usa dois sinais para dados ausentes:

- "-": fenômeno inexistente, gravado como zero com situacao = inexistente;
- "...": informação não disponível, gravado como nulo com situacao = nao_disponivel.
"""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import StrEnum


class Situacao(StrEnum):
    INFORMADO = "informado"
    INEXISTENTE = "inexistente"
    NAO_DISPONIVEL = "nao_disponivel"


@dataclass(frozen=True)
class Celula:
    valor: Decimal | None
    situacao: Situacao


MARCA_INEXISTENTE = {"-", "–", "—"}
MARCA_NAO_DISPONIVEL = {"...", "…"}


def normalizar_celula(bruto: object) -> Celula:
    """Converte o conteúdo de uma célula em valor decimal e situação do dado."""
    if bruto is None:
        return Celula(None, Situacao.NAO_DISPONIVEL)
    if isinstance(bruto, float) and bruto != bruto:  # NaN vindo do pandas
        return Celula(None, Situacao.NAO_DISPONIVEL)

    texto = str(bruto).strip()
    if texto in MARCA_INEXISTENTE:
        return Celula(Decimal(0), Situacao.INEXISTENTE)
    if texto in MARCA_NAO_DISPONIVEL or texto == "":
        return Celula(None, Situacao.NAO_DISPONIVEL)

    try:
        return Celula(Decimal(texto), Situacao.INFORMADO)
    except InvalidOperation as erro:
        raise ValueError(f"Valor não reconhecido na planilha: {bruto!r}") from erro
