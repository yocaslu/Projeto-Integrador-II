from decimal import Decimal

from apps.registros.queries import posicoes_com_empate, variacao_percentual


def test_variacao_percentual():
    assert variacao_percentual(Decimal(90), Decimal(100)) == Decimal("-10.0000")


def test_variacao_nula_sem_base():
    assert variacao_percentual(Decimal(10), Decimal(0)) is None
    assert variacao_percentual(None, Decimal(10)) is None
    assert variacao_percentual(Decimal(10), None) is None


def test_ranking_com_empates_e_sem_dado():
    valores = [Decimal(30), Decimal(50), None, Decimal(30), Decimal(10)]
    assert posicoes_com_empate(valores) == [2, 1, None, 2, 4]
