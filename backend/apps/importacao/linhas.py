"""Linhas intermediárias da importação.

Os leitores devolvem `Linha`s, ainda sem nada gravado no banco. As etapas seguintes (agregação
regional, validação e gravação) trabalham sobre essas linhas, o que permite testá-las sem a
planilha e sem o banco. Ver docs/importacao.md, seções 4.1 e 4.3.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum
from typing import NamedTuple

from apps.importacao.normalizacao import Situacao


class Nivel(StrEnum):
    UF = "uf"
    REGIAO = "regiao"
    PAIS = "pais"


class Metodo(StrEnum):
    """Como o valor de um registro foi obtido (RF11)."""

    PUBLICADO = "publicado"  # lido de uma célula da planilha
    SOMA_UFS = "soma_ufs"  # calculado pelo projeto como soma das UFs da região


class Localidade(NamedTuple):
    """UF, região ou Brasil. A sigla sozinha é ambígua (SE = Sergipe ou Sudeste)."""

    nivel: Nivel
    sigla: str


class Unidade(StrEnum):
    """Unidade do valor do registro (ADR 0004). Um fato com duas vítimas conta 2 e 1."""

    VITIMAS = "vitimas"
    OCORRENCIAS = "ocorrencias"


Recorte = tuple[tuple[str, str], ...]
"""Pares (dimensao, valor) em ordem; vazio = total do indicador."""


@dataclass(frozen=True, order=True)
class Chave:
    """Identidade de um registro, igual à chave única de REGISTROS_ANUAIS."""

    localidade: Localidade
    indicador: str
    recorte: Recorte
    unidade: Unidade
    ano: int


@dataclass
class Linha:
    chave: Chave
    valor: Decimal | None = None
    situacao: Situacao = Situacao.NAO_DISPONIVEL
    taxa_publicada: Decimal | None = None
    origem: str = ""
    observacao: str = ""
    marcas: set[str] = field(default_factory=set)
    metodo: Metodo = Metodo.PUBLICADO
