from decimal import Decimal

import openpyxl
import pandas as pd
import pytest

from apps.importacao.erros import ErroImportacao
from apps.importacao.leitores import ibge
from apps.importacao.linhas import Localidade, Nivel
from apps.localidades.referencia import REGIAO_DA_UF
from tests.conftest import PLANILHAS_DIR

POP2024 = PLANILHAS_DIR / "brutos" / "POP2024_reduzido.ods"
POP2025 = PLANILHAS_DIR / "brutos" / "POP2025_reduzido.ods"


def test_le_as_33_localidades_com_os_totais_publicados():
    lida = ibge.ler(POP2024)

    assert lida.ano == 2024
    assert len(lida.valores) == 33
    assert lida.valores[Localidade(Nivel.PAIS, "BR")] == Decimal(212583750)
    assert lida.valores[Localidade(Nivel.REGIAO, "N")] == Decimal(18669345)
    assert lida.valores[Localidade(Nivel.UF, "SE")] == Decimal(2291077)
    assert lida.marcas == {}


def test_marcas_de_nota_ficam_fora_do_valor():
    lida = ibge.ler(POP2025)

    assert lida.valores[Localidade(Nivel.UF, "PR")] == Decimal(11890517)
    assert lida.marcas == {Localidade(Nivel.UF, "PR"): "(1)", Localidade(Nivel.UF, "SC"): "(1)"}
    assert any(nota.startswith("(1)") for nota in lida.notas)


def copia(tmp_path, nome, alterar):
    df = pd.read_excel(POP2024, sheet_name=ibge.ABA, engine="odf", header=None, dtype=object)
    df = alterar(df)
    destino = tmp_path / nome
    with pd.ExcelWriter(destino, engine="odf") as escritor:
        df.to_excel(escritor, sheet_name=ibge.ABA, header=False, index=False)
    return destino


def test_ano_do_titulo_precisa_bater_com_o_nome_do_arquivo(tmp_path):
    with pytest.raises(ErroImportacao, match="nome do arquivo"):
        ibge.ler(copia(tmp_path, "POP2023_x.ods", lambda df: df))


def test_localidade_faltando_aborta(tmp_path):
    caminho = copia(tmp_path, "POP2024_x.ods", lambda df: df.drop(index=5))
    with pytest.raises(ErroImportacao, match="32 localidades lidas"):
        ibge.ler(caminho)


def test_localidade_desconhecida_aborta(tmp_path):
    def renomear(df):
        df.iat[5, 0] = "Atlântida"
        return df

    with pytest.raises(ErroImportacao, match="Localidade não reconhecida"):
        ibge.ler(copia(tmp_path, "POP2024_x.ods", renomear))


def test_populacao_invalida_aborta(tmp_path):
    def zerar(df):
        df.iat[5, 1] = 0
        return df

    with pytest.raises(ErroImportacao, match="população inválida"):
        ibge.ler(copia(tmp_path, "POP2024_x.ods", zerar))


def planilha_de_projecoes(destino, *, sem_grupo=None, sigla_extra=None, ano_inicial=2000):
    """Planilha no formato do IBGE: cada grupo etário vale 10 em "Ambos" e 999 em "Homens"."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Projeções das Populações, Revisão 2024"])
    ws.append([None, None, None, None, None, "ANO"])
    anos = list(range(ano_inicial, ano_inicial + 71))
    ws.append(["GRUPO ETÁRIO", "SEXO", "CÓD.", "SIGLA", "LOCAL", *anos])
    siglas = ["BR", "NO", "ND", "SD", "SU", "CO", *REGIAO_DA_UF]
    if sigla_extra:
        siglas.append(sigla_extra)
    for sigla in siglas:
        for grupo in range(ibge.GRUPOS_ETARIOS):
            if (sigla, grupo) != sem_grupo:
                ws.append([f" {grupo}", "Ambos", 0, sigla, sigla, *[10] * 71])
            ws.append([f" {grupo}", "Homens", 0, sigla, sigla, *[999] * 71])
    ws.append(["Fonte: IBGE"])
    wb.save(destino)
    return destino


def test_projecoes_somam_os_grupos_de_ambos_os_sexos_de_2012_a_2023(tmp_path):
    lidas = ibge.ler_projecoes(planilha_de_projecoes(tmp_path / "projecoes.xlsx"))

    assert [lida.ano for lida in lidas] == list(range(2012, 2024))
    assert {lida.fonte for lida in lidas} == {"ibge-projecoes"}
    for lida in lidas:
        assert len(lida.valores) == 33
        assert set(lida.valores.values()) == {Decimal(190)}
    # As siglas regionais do IBGE viram as do projeto; SE continua sendo Sergipe.
    assert Localidade(Nivel.REGIAO, "N") in lidas[0].valores
    assert Localidade(Nivel.REGIAO, "SE") in lidas[0].valores
    assert Localidade(Nivel.UF, "SE") in lidas[0].valores


@pytest.mark.parametrize(
    ("opcoes", "mensagem"),
    [
        ({"ano_inicial": 2001}, "anos do cabeçalho"),
        ({"sem_grupo": ("AC", 3)}, "sem os 19 grupos etários: AC"),
        ({"sigla_extra": "XX"}, "não reconhecida"),
    ],
)
def test_projecoes_inconsistentes_abortam(tmp_path, opcoes, mensagem):
    caminho = planilha_de_projecoes(tmp_path / "projecoes.xlsx", **opcoes)
    with pytest.raises(ErroImportacao, match=mensagem):
        ibge.ler_projecoes(caminho)
