from decimal import Decimal

import pandas as pd
import pytest

from apps.importacao.erros import ErroImportacao
from apps.importacao.leitores import ibge
from apps.importacao.linhas import Localidade, Nivel
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
