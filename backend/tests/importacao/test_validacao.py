from decimal import Decimal

from apps.importacao.validacao import Divergencia, diverge, taxa_por_100_mil


def test_taxa_por_100_mil():
    assert taxa_por_100_mil(Decimal(5800), 14_180_000) == Decimal("40.9")


def test_diverge_respeita_a_tolerancia():
    assert not diverge(Decimal("40.9"), Decimal("41.0"))
    assert diverge(Decimal("40.9"), Decimal("41.2"))


def test_diferenca_da_divergencia():
    item = Divergencia("BA", "mvi", 2025, Decimal("40.9"), Decimal("41.2"))
    assert item.diferenca == Decimal("0.3")
