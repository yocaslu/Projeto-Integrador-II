from decimal import Decimal

import pytest

from apps.api.v1.campos import (
    CampoDuasCasas,
    CampoInteiro,
    CampoPrecisaoGuardada,
    arredondar_2,
    formatar_duas_casas,
    formatar_inteiro,
    formatar_precisao_guardada,
)


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        (Decimal("5800"), "5800"),
        (Decimal("5800.0000"), "5800"),
        (Decimal("212583750"), "212583750"),
        (Decimal("0"), "0"),
        (Decimal("0.0000"), "0"),
        (Decimal("2.5"), "3"),  # meio para longe do zero
        (Decimal("-2.5"), "-3"),
        (Decimal("-0.4"), "0"),  # nunca "-0"
        (7, "7"),
    ],
)
def test_inteiro(valor, esperado):
    assert formatar_inteiro(valor) == esperado
    assert CampoInteiro().to_representation(valor) == esperado


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        (Decimal("40.9415826"), "40.94"),
        (Decimal("-3.1"), "-3.10"),
        (Decimal("16.19"), "16.19"),
        (Decimal("0"), "0.00"),
        (Decimal("1.005"), "1.01"),  # x.xx5 arredonda para longe do zero
        (Decimal("1.015"), "1.02"),
        (Decimal("2.675"), "2.68"),
        (Decimal("-1.005"), "-1.01"),
        (Decimal("1.0049999"), "1.00"),
        (Decimal("-0.004"), "0.00"),  # nunca "-0.00"
        (Decimal("-0.005"), "-0.01"),
        (Decimal("-0E-12"), "0.00"),
        (Decimal("123456789.999"), "123456790.00"),
    ],
)
def test_duas_casas(valor, esperado):
    assert formatar_duas_casas(valor) == esperado
    assert CampoDuasCasas().to_representation(valor) == esperado


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        (Decimal("40.941582600000"), "40.9415826"),
        (Decimal("19.105426800077"), "19.105426800077"),
        (Decimal("0E-12"), "0"),
        (Decimal("0.000000000000"), "0"),
        (Decimal("-0E-12"), "0"),
        (Decimal("100.000000000000"), "100"),  # sem notação exponencial
        (Decimal("0.000000000001"), "0.000000000001"),
        (Decimal("1E-13"), "0"),  # além de 12 casas
        (Decimal("5E-13"), "0.000000000001"),
        (Decimal("-3.5"), "-3.5"),
    ],
)
def test_precisao_guardada(valor, esperado):
    assert formatar_precisao_guardada(valor) == esperado
    assert CampoPrecisaoGuardada().to_representation(valor) == esperado


def test_nulo_vira_nulo():
    assert arredondar_2(None) is None
    for formatar in (formatar_inteiro, formatar_duas_casas, formatar_precisao_guardada):
        assert formatar(None) is None
    for campo in (CampoInteiro(), CampoDuasCasas(), CampoPrecisaoGuardada()):
        assert campo.to_representation(None) is None


def test_arredondar_2_devolve_decimal():
    assert arredondar_2(Decimal("40.945")) == Decimal("40.95")
    assert isinstance(arredondar_2(Decimal("1")), Decimal)
    assert str(arredondar_2(Decimal("-0.001"))) == "0.00"


@pytest.mark.parametrize("valor", [1.5, True, "1.5"])
def test_recusa_float_e_outros_tipos(valor):
    with pytest.raises(TypeError):
        formatar_duas_casas(valor)


def test_campos_sao_somente_leitura():
    for campo in (CampoInteiro(), CampoDuasCasas(), CampoPrecisaoGuardada()):
        assert campo.read_only
