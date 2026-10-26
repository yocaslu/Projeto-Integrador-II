"""Relatório de validação da importação (RF12).

Compara as taxas calculadas a partir da população do IBGE com as taxas publicadas pelo FBSP e
registra as divergências acima da tolerância em um arquivo CSV em dados/relatorios/.
"""

from dataclasses import dataclass
from decimal import Decimal

TOLERANCIA_PADRAO = Decimal("0.1")


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


def taxa_por_100_mil(valor: Decimal, populacao: int) -> Decimal:
    """Taxa por 100 mil habitantes, arredondada a uma casa decimal como no Anuário."""
    return (valor / Decimal(populacao) * 100_000).quantize(Decimal("0.1"))


def diverge(
    calculada: Decimal, publicada: Decimal, tolerancia: Decimal = TOLERANCIA_PADRAO
) -> bool:
    """Indica se a diferença entre as taxas passa da tolerância."""
    return abs(calculada - publicada) > tolerancia
