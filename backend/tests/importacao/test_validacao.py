from decimal import Decimal

from apps.importacao.validacao import TOLERANCIA, Divergencia, diverge, taxa_por_100_mil


def test_taxa_por_100_mil_em_precisao_total():
    taxa = taxa_por_100_mil(Decimal(5800), 14_180_000)

    assert taxa == Decimal(5800) / Decimal(14_180_000) * 100_000
    assert taxa != taxa.quantize(Decimal("0.1"))


def test_tolerancia_e_1e_6():
    assert Decimal("1e-6") == TOLERANCIA


def test_diverge_respeita_a_tolerancia_sem_arredondar():
    publicada = Decimal("40.941582612345")
    assert not diverge(publicada + Decimal("1e-6"), publicada)
    assert diverge(publicada + Decimal("1.1e-6"), publicada)
    assert diverge(Decimal("40.94"), Decimal("40.95"))


def test_diferenca_da_divergencia():
    item = Divergencia("BA", "mvi", 2025, Decimal("40.9"), Decimal("41.2"))
    assert item.diferenca == Decimal("0.3")
