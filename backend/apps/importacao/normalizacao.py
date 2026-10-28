"""Normalização das células da planilha do FBSP e dos nomes de localidade.

A planilha usa dois sinais para dados ausentes:

- "-": fenômeno inexistente, gravado como zero com situacao = inexistente;
- "...": informação não disponível, gravado como nulo com situacao = nao_disponivel.

Taxas numéricas são arredondadas a 12 casas aqui, e não no banco, para que a linha em memória seja
igual ao valor gravado em NUMERIC(24, 12) (ajuste 7 do modelo; docs/importacao.md, seção 4.4).
"""

import re
import unicodedata
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from apps.importacao.linhas import Localidade, Nivel
from apps.localidades import referencia
from apps.registros.escolhas import Situacao

__all__ = ["Celula", "Situacao", "normalizar_celula", "normalizar_taxa", "resolver_localidade"]

CASAS_TAXA = Decimal("1e-12")


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


def normalizar_taxa(bruto: object) -> Celula:
    """Como normalizar_celula, com a taxa arredondada a 12 casas (ROUND_HALF_UP)."""
    celula = normalizar_celula(bruto)
    if celula.valor is None:
        return celula
    return Celula(celula.valor.quantize(CASAS_TAXA, rounding=ROUND_HALF_UP), celula.situacao)


def chave_de_nome(nome: str) -> str:
    """Nome sem acento, em minúsculas e com espaços normalizados.

    "Região  Norte" → "regiao norte".
    """
    sem_acento = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", sem_acento).strip().lower()


def _aliases() -> dict[str, Localidade]:
    aliases: dict[str, Localidade] = {}
    for regiao in referencia.REGIOES:
        nivel = Nivel.PAIS if regiao.tipo == "pais" else Nivel.REGIAO
        for nome in (regiao.nome, *regiao.aliases):
            aliases[chave_de_nome(nome)] = Localidade(nivel, regiao.sigla)
    for estado in referencia.ESTADOS:
        aliases[chave_de_nome(estado.nome)] = Localidade(Nivel.UF, estado.sigla)
    return aliases


ALIASES = _aliases()


def resolver_localidade(nome: str) -> Localidade:
    """Localidade de um rótulo da planilha (FBSP ou IBGE); nome desconhecido → KeyError.

    Sem correspondência aproximada: um nome novo entra em localidades/referencia.py por PR
    (docs/importacao.md, seção 4.5).
    """
    try:
        return ALIASES[chave_de_nome(nome)]
    except KeyError:
        raise KeyError(f"Localidade não reconhecida: {nome!r}") from None
