import pytest
from django.http import QueryDict
from rest_framework.exceptions import ValidationError

from apps.api.v1.parametros import (
    COMBINACAO,
    Anos,
    LeitorParametros,
    Localidades,
    Paginacao,
)

UFS = {"AC", "BA", "RJ", "SE", "SP"}
REGIOES = {"N", "NE", "SE", "S", "CO"}
INTERVALO = (2012, 2025)
PARAMETROS_REGISTROS = {
    "nivel",
    "uf",
    "regiao",
    "indicador",
    "incluir_subtipos",
    "ano",
    "ano_min",
    "ano_max",
    "unidade",
    "recorte",
    "situacao",
    "ordenar",
}


def leitor(consulta: str, permitidos=PARAMETROS_REGISTROS, **kwargs) -> LeitorParametros:
    return LeitorParametros(QueryDict(consulta), permitidos, **kwargs)


def erros(leitor_: LeitorParametros) -> dict[str, list[str]]:
    with pytest.raises(ValidationError) as excinfo:
        leitor_.validar()
    return {chave: [str(m) for m in mensagens] for chave, mensagens in excinfo.value.detail.items()}


# Regras gerais (contrato, seção 2)


def test_sem_parametros_valida():
    leitor("").validar()


def test_parametro_desconhecido():
    assert erros(leitor("uf_=SP")) == {"uf_": ["Parâmetro desconhecido."]}


def test_todos_os_erros_vem_juntos():
    resultado = erros(leitor("xpto=1&uf=&nivel=uf&nivel=pais"))
    assert set(resultado) == {"xpto", "uf", "nivel"}


def test_parametro_repetido():
    assert "repetido" in erros(leitor("uf=SP&uf=RJ"))["uf"][0]


def test_valor_vazio():
    assert erros(leitor("uf="))["uf"] == ["Valor vazio."]


def test_valor_so_com_espacos_e_vazio():
    assert erros(leitor("uf=%20%20"))["uf"] == ["Valor vazio."]


def test_formato_e_aceito_em_qualquer_recurso():
    leitor("formato=json", permitidos=set()).validar()
    leitor("formato=csv", permitidos=set()).validar()


def test_paginacao_em_recurso_sem_paginacao():
    resultado = erros(leitor("pagina=1&tamanho=10", permitidos=set()))
    assert set(resultado) == {"pagina", "tamanho"}


def test_paginacao_padrao():
    assert leitor("", paginado=True).paginacao() == Paginacao(pagina=1, tamanho=100)


def test_paginacao_informada():
    assert leitor("pagina=3&tamanho=1000", paginado=True).paginacao() == Paginacao(3, 1000)


@pytest.mark.parametrize("consulta", ["tamanho=1001", "tamanho=0", "tamanho=abc", "pagina=0"])
def test_paginacao_invalida(consulta):
    lp = leitor(consulta, paginado=True)
    lp.paginacao()
    nome = consulta.split("=")[0]
    assert nome in erros(lp)


@pytest.mark.parametrize("consulta", ["formato=csv&pagina=1", "formato=CSV&tamanho=10"])
def test_paginacao_com_csv_pelo_formato(consulta):
    lp = leitor(consulta, paginado=True)
    lp.paginacao()
    assert "CSV" in next(iter(erros(lp).values()))[0]


def test_paginacao_com_csv_pelo_accept():
    lp = leitor("pagina=2", paginado=True, csv=True)
    lp.paginacao()
    assert "pagina" in erros(lp)


def test_csv_sem_paginacao_e_valido():
    leitor("formato=csv", paginado=True).validar()


# Listas e valores (regras 3 e 6)


def test_lista_remove_espacos_e_repetidos():
    lp = leitor("indicador=mvi, roubo ,mvi")
    assert lp.lista("indicador") == ("mvi", "roubo")
    lp.validar()


def test_lista_com_item_vazio():
    lp = leitor("uf=SP,")
    assert lp.lista("uf", UFS, maiusculas=True) is None
    assert erros(lp)["uf"] == ["Item vazio na lista."]


def test_lista_siglas_sem_diferenca_de_caixa():
    assert leitor("uf=sp,Rj").lista("uf", UFS, maiusculas=True) == ("SP", "RJ")


def test_lista_valor_inexistente():
    lp = leitor("uf=SP,XX,YY")
    assert lp.lista("uf", UFS, maiusculas=True) is None
    assert erros(lp)["uf"] == ["Valor não reconhecido: XX.", "Valor não reconhecido: YY."]


def test_slug_diferencia_caixa():
    lp = leitor("indicador=MVI")
    assert lp.lista("indicador", {"mvi"}) is None
    assert "indicador" in erros(lp)


def test_lista_ausente():
    assert leitor("").lista("uf") is None


def test_unico():
    assert leitor("indicador=mvi").unico("indicador", {"mvi"}) == "mvi"


def test_unico_com_lista():
    lp = leitor("indicador=mvi,roubo")
    assert lp.unico("indicador") is None
    assert erros(lp)["indicador"] == ["Informe um único valor."]


def test_unico_obrigatorio():
    lp = leitor("", permitidos={"indicador"})
    assert lp.unico("indicador", obrigatorio=True) is None
    assert erros(lp)["indicador"] == ["Parâmetro obrigatório."]


def test_unico_invalido_e_maiusculas():
    lp = leitor("uf=sp")
    assert lp.unico("uf", UFS, maiusculas=True) == "SP"
    l2 = leitor("uf=xx")
    assert l2.unico("uf", UFS, maiusculas=True) is None
    assert erros(l2)["uf"] == ["Valor não reconhecido: XX."]


# Booleanos (regra 7)


@pytest.mark.parametrize(("texto", "esperado"), [("true", True), ("false", False)])
def test_booleano_valido(texto, esperado):
    lp = leitor(f"incluir_subtipos={texto}")
    assert lp.booleano("incluir_subtipos") is esperado
    lp.validar()


def test_booleano_padrao():
    assert leitor("").booleano("incluir_subtipos") is False


@pytest.mark.parametrize("texto", ["1", "0", "True", "sim", "FALSE"])
def test_booleano_invalido(texto):
    lp = leitor(f"incluir_subtipos={texto}")
    lp.booleano("incluir_subtipos")
    assert erros(lp)["incluir_subtipos"] == ["Use true ou false."]


# Anos (regras 8 e 9)


def test_anos_ausentes():
    assert leitor("").anos(INTERVALO) == Anos()


def test_ano_lista():
    assert leitor("ano=2025,2024,2025").anos(INTERVALO) == Anos(ano=(2025, 2024))


def test_ano_intervalo():
    assert leitor("ano_min=2015&ano_max=2020").anos(INTERVALO) == Anos(ano_min=2015, ano_max=2020)


def test_ano_min_sozinho():
    assert leitor("ano_min=2020").anos(INTERVALO) == Anos(ano_min=2020)


def test_ano_fora_do_intervalo():
    lp = leitor("ano=20255")
    lp.anos(INTERVALO)
    assert erros(lp)["ano"] == ["Ano inválido: 20255."]
    l2 = leitor("ano=2011")
    l2.anos(INTERVALO)
    assert erros(l2)["ano"] == ["Ano fora do intervalo disponível (2012 a 2025)."]


def test_ano_fora_do_intervalo_usa_o_intervalo_informado():
    lp = leitor("ano_max=2023")
    lp.anos((2024, 2025))
    assert erros(lp)["ano_max"] == ["Ano fora do intervalo disponível (2024 a 2025)."]


@pytest.mark.parametrize("texto", ["abc", "25", "2025.0", "-2025"])
def test_ano_invalido(texto):
    lp = leitor(f"ano={texto}")
    lp.anos(INTERVALO)
    assert "ano" in erros(lp)


def test_ano_com_intervalo():
    lp = leitor("ano=2025&ano_min=2020")
    assert lp.anos(INTERVALO) == Anos()
    assert COMBINACAO in erros(lp)


def test_ano_min_maior_que_ano_max():
    lp = leitor("ano_min=2025&ano_max=2020")
    assert lp.anos(INTERVALO) == Anos()
    assert erros(lp)[COMBINACAO] == ["ano_min não pode ser maior que ano_max."]


def test_ano_unico():
    assert leitor("ano=2024", {"ano"}).ano("ano", INTERVALO) == 2024
    lp = leitor("ano=2024,2025", {"ano"})
    assert lp.ano("ano", INTERVALO) is None
    assert "ano" in erros(lp)


# Nível, UF e região (seção 4.7.2), uma linha da tabela por teste


def localidades(consulta: str) -> Localidades:
    lp = leitor(consulta)
    resultado = lp.localidades(UFS, REGIOES)
    lp.validar()
    return resultado


def erros_localidades(consulta: str) -> dict[str, list[str]]:
    lp = leitor(consulta)
    lp.localidades(UFS, REGIOES)
    return erros(lp)


def test_nivel_padrao_e_uf():
    assert localidades("") == Localidades(niveis=("uf",))


def test_uf_implica_nivel_uf():
    assert localidades("uf=SP,RJ") == Localidades(niveis=("uf",), ufs=("SP", "RJ"))


def test_nivel_uf_com_uf():
    assert localidades("nivel=uf&uf=sp") == Localidades(niveis=("uf",), ufs=("SP",))


def test_nivel_uf_com_regiao_traz_as_ufs_da_regiao():
    assert localidades("nivel=uf&regiao=NE") == Localidades(niveis=("uf",), regioes=("NE",))


def test_nivel_regiao():
    assert localidades("nivel=regiao") == Localidades(niveis=("regiao",))


def test_nivel_regiao_com_regioes():
    assert localidades("nivel=regiao&regiao=ne,SE") == Localidades(
        niveis=("regiao",), regioes=("NE", "SE")
    )


def test_nivel_pais():
    assert localidades("nivel=pais") == Localidades(niveis=("pais",))


def test_mistura_explicita_de_niveis_em_ordem_canonica():
    assert localidades("nivel=uf,pais,regiao") == Localidades(niveis=("pais", "regiao", "uf"))


def test_regiao_sem_nivel_e_ambigua():
    assert "Ambíguo" in erros_localidades("regiao=NE")["regiao"][0]


def test_uf_e_regiao_juntos():
    assert "mutuamente exclusivos" in erros_localidades("uf=SP&regiao=NE&nivel=uf")[COMBINACAO][0]


def test_uf_com_nivel_diferente_de_uf():
    assert erros_localidades("nivel=regiao&uf=SP")[COMBINACAO] == [
        "uf só pode ser usado com nivel=uf."
    ]


def test_regiao_com_nivel_pais():
    assert erros_localidades("nivel=pais&regiao=NE")[COMBINACAO] == [
        "regiao não pode ser usado com nivel=pais."
    ]


@pytest.mark.parametrize("consulta", ["nivel=uf,regiao&uf=SP", "nivel=pais,regiao&regiao=NE"])
def test_uf_ou_regiao_com_mais_de_um_nivel(consulta):
    assert "/comparacao/" in erros_localidades(consulta)[COMBINACAO][0]


def test_regiao_br():
    assert "nivel=pais" in erros_localidades("nivel=regiao&regiao=BR")["regiao"][0]


def test_regiao_br_em_minusculas_na_lista():
    assert "regiao" in erros_localidades("nivel=regiao&regiao=NE,br")


def test_nivel_invalido():
    assert erros_localidades("nivel=municipio")["nivel"] == ["Valor não reconhecido: municipio."]


def test_sigla_se_e_sergipe_em_uf_e_sudeste_em_regiao():
    assert localidades("uf=SE").ufs == ("SE",)
    assert localidades("nivel=regiao&regiao=SE").regioes == ("SE",)


# Ordenação (seção 4.7.3)

CAMPOS = {"ano", "indicador", "localidade", "valor", "taxa"}


def test_ordenacao_ausente():
    assert leitor("").ordenacao(CAMPOS) == ()


def test_ordenacao_com_inversao():
    lp = leitor("ordenar=-taxa,ano")
    assert lp.ordenacao(CAMPOS) == ("-taxa", "ano")
    lp.validar()


def test_ordenacao_campo_desconhecido():
    lp = leitor("ordenar=populacao")
    assert lp.ordenacao(CAMPOS) == ()
    assert erros(lp)["ordenar"] == ["Campo de ordenação não reconhecido: populacao."]


def test_ordenacao_campo_repetido():
    lp = leitor("ordenar=ano,-ano")
    assert lp.ordenacao(CAMPOS) == ()
    assert erros(lp)["ordenar"] == ["Campo de ordenação repetido: ano."]


def test_ordenacao_so_hifen():
    lp = leitor("ordenar=-")
    lp.ordenacao(CAMPOS)
    assert "ordenar" in erros(lp)


def test_informado():
    lp = leitor("uf=")
    assert lp.informado("uf")
    assert not lp.informado("regiao")
