from collections import Counter

from apps.localidades.referencia import ESTADOS, REGIAO_DA_UF, REGIOES


def test_brasil_e_cinco_regioes_em_ordem_canonica():
    assert [r.sigla for r in REGIOES] == ["BR", "N", "NE", "SE", "S", "CO"]
    assert [r.codigo_ibge for r in REGIOES] == ["1", "1", "2", "3", "4", "5"]
    assert [r.tipo for r in REGIOES] == ["pais"] + ["regiao"] * 5


def test_vinte_e_sete_ufs_por_sigla_com_codigos_unicos():
    siglas = [e.sigla for e in ESTADOS]
    codigos = [e.codigo_ibge for e in ESTADOS]

    assert len(ESTADOS) == 27
    assert siglas == sorted(siglas)
    assert len(set(codigos)) == 27
    assert all(len(c) == 2 and c.isdigit() for c in codigos)


def test_ufs_por_regiao():
    assert Counter(REGIAO_DA_UF.values()) == {"N": 7, "NE": 9, "SE": 4, "S": 3, "CO": 4}
    assert REGIAO_DA_UF["SE"] == "NE"  # Sergipe fica no Nordeste; SE também é o Sudeste


def test_codigo_ibge_comeca_pelo_codigo_da_regiao():
    codigo_da_regiao = {r.sigla: r.codigo_ibge for r in REGIOES}
    for estado in ESTADOS:
        assert estado.codigo_ibge[0] == codigo_da_regiao[estado.regiao]
