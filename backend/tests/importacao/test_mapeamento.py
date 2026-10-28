import re

from apps.catalogo.referencia import AGRUPADORES, INDICADORES
from apps.importacao.mapeamento import ANCORA_REGIOES, ANCORA_UFS, TABELAS, contagem_esperada


def test_contagem_esperada_da_planilha_completa():
    assert contagem_esperada() == (1750, 230)  # 1.980 registros (docs/importacao.md, 3)


def test_ancora_nao_casa_com_a_linha_de_abrangencia():
    assert re.match(ANCORA_UFS, " Brasil e Unidades da Federação")
    assert not re.match(ANCORA_UFS, "Brasil e Unidades da Federação –  2024-2025")
    assert re.match(ANCORA_REGIOES, "Brasil, Regiões e Unidades da Federação")
    assert not re.match(ANCORA_REGIOES, "Brasil, Regiões e Unidades da Federação - 2012-2025")


def test_tabela_dona_unica_por_indicador_recorte_e_unidade():
    donos = {}
    for tabela in TABELAS:
        if tabela.conferencia:
            continue
        for bloco in tabela.blocos_gravados():
            chave = (bloco.indicador, bloco.recorte, bloco.unidade)
            assert chave not in donos, f"{chave} em {donos.get(chave)} e {tabela.aba}"
            donos[chave] = tabela.aba


def test_t01_e_t09_so_conferencia():
    assert {t.aba for t in TABELAS if t.conferencia} == {"T01", "T09"}


def test_todo_slug_do_mapeamento_existe_e_nao_e_agrupador():
    slugs = {i.slug for i in INDICADORES}
    usados = {bloco.indicador for tabela in TABELAS for bloco in tabela.blocos}
    assert usados <= slugs
    assert not usados & AGRUPADORES
