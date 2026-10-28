from decimal import Decimal

import pytest

from apps.importacao.linhas import Localidade, Nivel
from apps.importacao.normalizacao import (
    Situacao,
    normalizar_celula,
    normalizar_taxa,
    resolver_localidade,
)


@pytest.mark.parametrize(
    ("bruto", "valor", "situacao"),
    [
        (42, Decimal(42), Situacao.INFORMADO),
        ("40.9", Decimal("40.9"), Situacao.INFORMADO),
        ("-", Decimal(0), Situacao.INEXISTENTE),
        ("...", None, Situacao.NAO_DISPONIVEL),
        ("", None, Situacao.NAO_DISPONIVEL),
        (None, None, Situacao.NAO_DISPONIVEL),
        (float("nan"), None, Situacao.NAO_DISPONIVEL),
    ],
)
def test_normalizar_celula(bruto, valor, situacao):
    celula = normalizar_celula(bruto)
    assert celula.valor == valor
    assert celula.situacao is situacao


def test_valor_desconhecido_gera_erro():
    with pytest.raises(ValueError, match="não reconhecido"):
        normalizar_celula("n/d")


@pytest.mark.parametrize(
    ("bruto", "esperado"),
    [
        (19.105426800076884, Decimal("19.105426800077")),  # 17 dígitos do float do Excel
        (2.0000000000005, Decimal("2.000000000001")),  # meio para longe do zero
        (-8.15234566913513, Decimal("-8.152345669135")),
        ("-", Decimal("0.000000000000")),
    ],
)
def test_taxa_arredondada_a_12_casas(bruto, esperado):
    assert normalizar_taxa(bruto).valor == esperado


def test_taxa_nao_disponivel_continua_nula():
    assert normalizar_taxa("...").valor is None


@pytest.mark.parametrize(
    ("nome", "localidade"),
    [
        ("Brasil", Localidade(Nivel.PAIS, "BR")),
        ("Região Norte", Localidade(Nivel.REGIAO, "N")),
        ("Norte", Localidade(Nivel.REGIAO, "N")),
        ("Região Centro-Oeste", Localidade(Nivel.REGIAO, "CO")),
        ("Centro Oeste", Localidade(Nivel.REGIAO, "CO")),
        ("Sudeste", Localidade(Nivel.REGIAO, "SE")),
        ("Sergipe", Localidade(Nivel.UF, "SE")),
        ("  São   Paulo ", Localidade(Nivel.UF, "SP")),
        ("SAO PAULO", Localidade(Nivel.UF, "SP")),
    ],
)
def test_resolver_localidade(nome, localidade):
    assert resolver_localidade(nome) == localidade


def test_localidade_desconhecida_nao_tem_correspondencia_aproximada():
    with pytest.raises(KeyError, match="não reconhecida"):
        resolver_localidade("Sao Paulo do Sul")
