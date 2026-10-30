"""Junção das edições do Anuário: edição dona e revisões (ADR 0012)."""

from decimal import Decimal

from apps.importacao.edicoes import incorporar
from apps.importacao.linhas import Chave, Linha, Localidade, Metodo, Nivel
from apps.registros.escolhas import Situacao, Unidade

BA = Localidade(Nivel.UF, "BA")
BR = Localidade(Nivel.PAIS, "BR")


def linha(localidade, ano, valor, origem="T01!B2", metodo=Metodo.PUBLICADO):
    return Linha(
        chave=Chave(localidade, "latrocinio", (), Unidade.VITIMAS, ano),
        valor=None if valor is None else Decimal(valor),
        situacao=Situacao.INFORMADO if valor is not None else Situacao.NAO_DISPONIVEL,
        origem=origem,
        metodo=metodo,
    )


def test_ano_sem_dona_entra_com_o_arquivo_na_origem():
    juntas, revisoes = incorporar([linha(BA, 2024, 10)], [linha(BA, 2023, 9)], 2025, "a.xlsx")

    assert [(item.chave.ano, item.origem) for item in juntas] == [
        (2024, "T01!B2"),
        (2023, "a.xlsx:T01!B2"),
    ]
    assert revisoes == []


def test_valor_igual_nao_e_revisao():
    donas = [linha(BA, 2024, 10)]
    juntas, revisoes = incorporar(donas, [linha(BA, 2024, 10)], 2025, "a.xlsx")

    assert len(juntas) == 1
    assert revisoes == []
    assert not juntas[0].observacao


def test_revisao_nao_substitui_a_dona_e_vai_para_a_observacao():
    juntas, revisoes = incorporar([linha(BA, 2024, 28)], [linha(BA, 2024, 13)], 2025, "a.xlsx")

    assert juntas[0].valor == Decimal(28)
    assert "edição de 2025 do Anuário publicou 13" in juntas[0].observacao
    assert (revisoes[0].verificacao, revisoes[0].esperado, revisoes[0].obtido) == (
        "revisao_entre_edicoes",
        Decimal(13),
        Decimal(28),
    )


def test_nao_disponivel_na_dona_nao_e_preenchido_pela_edicao_anterior():
    juntas, revisoes = incorporar([linha(BA, 2024, None)], [linha(BA, 2024, 1496)], 2025, "a.xlsx")

    assert juntas[0].valor is None
    assert "publicou 1496" in juntas[0].observacao
    assert len(revisoes) == 1


def test_dona_e_escolhida_por_ano_e_nao_por_localidade():
    # A dona não publicou o Brasil neste teste, mas o ano já tem dona: a linha não entra.
    juntas, _ = incorporar([linha(BA, 2024, 10)], [linha(BR, 2024, 99)], 2025, "a.xlsx")

    assert [item.chave.localidade for item in juntas] == [BA]


def test_regiao_calculada_nao_gera_nota_de_revisao():
    calculada = Localidade(Nivel.REGIAO, "NE")
    donas = [linha(calculada, 2024, 10, metodo=Metodo.SOMA_UFS)]
    _, revisoes = incorporar(
        donas, [linha(calculada, 2024, 11, metodo=Metodo.SOMA_UFS)], 2025, "a.xlsx"
    )

    assert revisoes == []
    assert not donas[0].observacao
