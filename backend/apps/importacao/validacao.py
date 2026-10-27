"""Relatório de validação da importação (RF12).

Compara as taxas calculadas a partir da população do IBGE com as taxas publicadas pelo FBSP e
registra as divergências acima da tolerância em um arquivo CSV em dados/relatorios/.

Todas as comparações são feitas em precisão total, sem arredondar nenhum lado, com tolerância
absoluta de 1e-6 (ADR 0004; docs/importacao.md, seção 5). As taxas do FBSP batem com o cálculo
pela população do IBGE até ~1e-14, e o arredondamento de taxa_publicada a 12 casas acrescenta no
máximo 5e-13.
"""

from dataclasses import dataclass
from decimal import Decimal

TOLERANCIA = Decimal("1e-6")


@dataclass(frozen=True)
class Divergencia:
    localidade: str
    indicador: str
    ano: int
    taxa_calculada: Decimal
    taxa_publicada: Decimal

    @property
    def diferenca(self) -> Decimal:
        return abs(self.taxa_calculada - self.taxa_publicada)


def taxa_por_100_mil(valor: Decimal, populacao: int | Decimal) -> Decimal:
    """Taxa por 100 mil habitantes, em precisão total (sem arredondar)."""
    return valor / Decimal(populacao) * 100_000


def diverge(calculada: Decimal, publicada: Decimal, tolerancia: Decimal = TOLERANCIA) -> bool:
    """Indica se a diferença entre os dois valores passa da tolerância."""
    return abs(calculada - publicada) > tolerancia
