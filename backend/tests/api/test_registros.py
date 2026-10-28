"""/registros/, /registros/{id}/ e /populacao/ (contrato, seções 4.6 e 4.7; testes da seção 8)."""

import pytest

from apps.registros.models import RegistroAnual

URL = "/api/v1/registros/"


def buscar(client, consulta="", status=200):
    resposta = client.get(f"{URL}?{consulta}")
    assert resposta.status_code == status, resposta.content
    return resposta.json()


def locais(corpo):
    return [(r["localidade"]["nivel"], r["localidade"]["codigo"]) for r in corpo["results"]]


def erros(corpo):
    return {e["parametro"] for e in corpo["erros"]}


# Regra de nível, UF e região: uma linha da tabela 4.7.2 por teste

UFS = [("uf", "AC"), ("uf", "BA"), ("uf", "SE"), ("uf", "SP")]


@pytest.mark.parametrize(
    ("consulta", "esperado"),
    [
        ("", UFS),
        ("uf=sp,BA", [("uf", "BA"), ("uf", "SP")]),
        ("nivel=uf&uf=SP", [("uf", "SP")]),
        ("nivel=uf&regiao=NE", [("uf", "BA"), ("uf", "SE")]),  # SE = Sergipe, no Nordeste
        ("nivel=regiao", [("regiao", "NE"), ("regiao", "SE")]),
        ("nivel=regiao&regiao=SE", [("regiao", "SE")]),  # SE = Sudeste
        ("nivel=pais", [("pais", "BR")]),
        ("nivel=pais,regiao,uf", [("pais", "BR"), ("regiao", "NE"), ("regiao", "SE"), *UFS]),
    ],
)
def test_regra_de_nivel(client, serie, consulta, esperado):
    assert locais(buscar(client, f"indicador=mvi&ano=2025&{consulta}")) == esperado


@pytest.mark.parametrize(
    ("consulta", "parametro"),
    [
        ("regiao=NE", "regiao"),  # ambíguo sem nivel
        ("uf=SP&regiao=NE", ""),
        ("nivel=regiao&uf=SP", ""),
        ("nivel=pais&regiao=NE", ""),
        ("nivel=pais,uf&uf=SP", ""),
        ("nivel=regiao,uf&regiao=NE", ""),
        ("regiao=BR&nivel=regiao", "regiao"),
    ],
)
def test_combinacoes_de_nivel_proibidas(client, serie, consulta, parametro):
    assert parametro in erros(buscar(client, consulta, 400))


# Recorte, unidade e subtipos


def test_recorte_padrao_total_todos_e_ids(client, serie):
    base = "indicador=morte-intervencao-policial"
    pm = next(r for r in buscar(client, f"{base}&recorte=todos")["results"] if r["recorte"])

    total = buscar(client, base)["results"]
    todos = buscar(client, f"{base}&recorte=todos")["results"]
    so_um = buscar(client, f"{base}&recorte={pm['recorte']['id']}")["results"]

    assert [r["recorte"] for r in total] == [None]
    assert len(todos) == 3 and todos[0]["recorte"] is None  # total primeiro, depois por chave
    assert [r["recorte"]["id"] for r in so_um] == [pm["recorte"]["id"]]
    assert so_um[0]["recorte"]["itens"][0] == {
        "dimensao": "corporacao",
        "valor": pm["recorte"]["itens"][0]["valor"],
    }


@pytest.mark.parametrize("consulta", ["recorte=99999", "recorte=todos,1", "recorte=total,1"])
def test_recorte_invalido(client, serie, consulta):
    assert "recorte" in erros(buscar(client, consulta, 400))


def test_incluir_subtipos_traz_todos_os_descendentes(client, serie):
    corpo = buscar(client, "indicador=homicidio-doloso&incluir_subtipos=true&uf=BA")
    assert [r["indicador"]["slug"] for r in corpo["results"]] == [
        "homicidio-doloso",
        "homicidio-mulheres",
        "feminicidio",
    ]


def test_furto_exige_incluir_subtipos(client, serie):
    corpo = buscar(client, "indicador=furto", 400)
    assert corpo["erros"] == [
        {
            "parametro": "indicador",
            "mensagem": "O indicador furto não tem registros próprios; use incluir_subtipos=true.",
        }
    ]
    subtipos = buscar(client, "indicador=furto&incluir_subtipos=true")["results"]
    assert [r["indicador"]["slug"] for r in subtipos] == ["furto-veiculo", "furto-celular"]


def test_incluir_subtipos_exige_indicador(client, serie):
    assert "incluir_subtipos" in erros(buscar(client, "incluir_subtipos=true", 400))
    assert "incluir_subtipos" in erros(buscar(client, "indicador=mvi&incluir_subtipos=1", 400))


def test_unidade_padrao_todas_e_lista(client, serie):
    base = "indicador=homicidio-doloso&uf=BA"
    padrao = buscar(client, base)["results"]
    todas = buscar(client, f"{base}&unidade=todas")["results"]
    ocorrencias = buscar(client, f"{base}&unidade=ocorrencias")["results"]

    assert [r["unidade"] for r in padrao] == ["vitimas"]
    assert [r["unidade"] for r in todas] == ["vitimas", "ocorrencias"]
    assert [r["unidade"] for r in ocorrencias] == ["ocorrencias"]


def test_unidade_padrao_de_cada_indicador(client, serie):
    corpo = buscar(client, "uf=BA&ano=2025&indicador=mvi,roubo")
    assert [(r["indicador"]["slug"], r["unidade"]) for r in corpo["results"]] == [
        ("mvi", "vitimas"),
        ("roubo", "ocorrencias"),
    ]


def test_indicador_sem_registros_na_unidade_pedida(client, serie):
    corpo = buscar(client, "indicador=mvi&unidade=ocorrencias", 400)
    assert corpo["erros"] == [
        {"parametro": "unidade", "mensagem": "O indicador mvi não tem registros em ocorrencias."}
    ]
    assert buscar(client, "indicador=mvi,homicidio-doloso&unidade=ocorrencias")["count"] == 1


@pytest.mark.parametrize("consulta", ["unidade=padrao,vitimas", "unidade=todas,ocorrencias"])
def test_padrao_e_todas_nao_se_misturam(client, serie, consulta):
    assert "unidade" in erros(buscar(client, consulta, 400))


# Anos e situação


def test_filtros_de_ano_e_situacao(client, serie):
    assert buscar(client, "indicador=mvi&uf=BA&ano=2024")["count"] == 1
    assert buscar(client, "indicador=mvi&uf=BA&ano_min=2025")["count"] == 1
    assert buscar(client, "indicador=mvi&ano=2025&situacao=nao_disponivel")["count"] == 1


@pytest.mark.parametrize(
    ("consulta", "mensagem"),
    [
        ("ano=2023", "Ano fora do intervalo disponível (2024 a 2025)."),
        ("ano=2025&ano_min=2024", "ano não pode ser usado junto com ano_min ou ano_max."),
        ("ano_min=2025&ano_max=2024", "ano_min não pode ser maior que ano_max."),
    ],
)
def test_anos_invalidos(client, serie, consulta, mensagem):
    assert mensagem in [e["mensagem"] for e in buscar(client, consulta, 400)["erros"]]


# Formato do registro (contrato, 1.2, 3 e 4.7.4)


def test_registro_completo(client, serie):
    [registro] = buscar(client, "indicador=mvi&uf=BA&ano=2025")["results"]
    fontes = serie.fontes

    assert registro == {
        "id": registro["id"],
        "ano": 2025,
        "localidade": {"nivel": "uf", "codigo": "BA", "codigo_ibge": "29", "nome": "Bahia"},
        "indicador": {"slug": "mvi", "nome": "Mortes Violentas Intencionais"},
        "recorte": None,
        "unidade": "vitimas",
        "valor": "120",
        "situacao": "informado",
        "metodo": "publicado",
        "taxa": {
            "valor": "8.00",
            "base": "100 mil habitantes",
            "origem": "calculada",
            "fonte": {"id": fontes["ibge-estimativas"].id, "nome": fontes["ibge-estimativas"].nome},
        },
        "taxa_publicada": "8.000000000123",
        "variacao": {"ano_referencia": 2024, "valor_pct": "20.00", "taxa_pct": "-20.00"},
        "participacao": {"referencia": None, "valor_pct": None},
        "fonte": {
            "id": fontes["secretarias-seguranca"].id,
            "nome": fontes["secretarias-seguranca"].nome,
        },
        "observacao": None,
    }


def test_registro_nao_disponivel_e_publicado(client, serie):
    [acre] = buscar(client, "indicador=mvi&uf=AC")["results"]
    [sergipe] = buscar(client, "indicador=mvi&uf=SE")["results"]

    assert (acre["valor"], acre["situacao"]) == (None, "nao_disponivel")
    assert acre["taxa"] == {
        "valor": None,
        "base": "100 mil habitantes",
        "origem": None,
        "fonte": None,
    }
    assert acre["variacao"] == {"ano_referencia": 2024, "valor_pct": None, "taxa_pct": None}
    assert sergipe["taxa"]["valor"] == "3.00"  # 30 / 1 000 000 × 100 000


def test_participacao_no_pai_e_no_total(client, serie):
    [homicidio] = buscar(client, "indicador=homicidio-doloso&uf=BA")["results"]
    recortes = buscar(client, "indicador=morte-intervencao-policial&recorte=todos")["results"]

    assert homicidio["participacao"] == {
        "referencia": {"tipo": "indicador_pai", "indicador": "mvi"},
        "valor_pct": "50.00",
    }
    # Total de MDIP: 30 das 120 MVI; recorte sem dado: nulo; PM em serviço: 12 dos 30.
    assert [r["participacao"]["valor_pct"] for r in recortes] == ["25.00", None, "40.00"]
    assert recortes[0]["participacao"]["referencia"] == {
        "tipo": "indicador_pai",
        "indicador": "mvi",
    }
    assert recortes[2]["participacao"]["referencia"] == {
        "tipo": "total_do_indicador",
        "indicador": "morte-intervencao-policial",
    }


# Ordenação e paginação


def test_ordenar_por_taxa_com_nulos_ao_final(client, serie):
    crescente = buscar(client, "indicador=mvi&ano=2025&ordenar=taxa")
    decrescente = buscar(client, "indicador=mvi&ano=2025&ordenar=-taxa")

    assert locais(crescente) == [("uf", "SP"), ("uf", "SE"), ("uf", "BA"), ("uf", "AC")]
    assert locais(decrescente) == [("uf", "BA"), ("uf", "SE"), ("uf", "SP"), ("uf", "AC")]


@pytest.mark.parametrize("consulta", ["ordenar=nome", "ordenar=ano,-ano", "ordenar="])
def test_ordenar_invalido(client, serie, consulta):
    assert "ordenar" in erros(buscar(client, consulta, 400))


def test_percorrer_todas_as_paginas_sem_repetir_nem_perder(client, serie):
    consulta = "nivel=pais,regiao,uf&unidade=todas&recorte=todos&ordenar=-ano&tamanho=2"
    vistos, url = [], f"{URL}?{consulta}"
    while url:
        corpo = client.get(url).json()
        vistos += [r["id"] for r in corpo["results"]]
        url = corpo["next"]

    assert len(vistos) == len(set(vistos)) == RegistroAnual.objects.count() == corpo["count"]


def test_envelope_e_links_preservam_os_parametros(client, serie):
    primeira = buscar(client, "indicador=mvi&nivel=pais,regiao,uf&tamanho=3")
    segunda = client.get(primeira["next"]).json()

    assert primeira["count"] == 8 and primeira["previous"] is None
    assert primeira["next"].startswith("http://testserver/api/v1/registros/?")
    assert "indicador=mvi" in primeira["next"] and "pagina=2" in primeira["next"]
    assert (
        segunda["previous"]
        == "http://testserver/api/v1/registros/?indicador=mvi&nivel=pais%2Cregiao%2Cuf&tamanho=3"
    )
    assert len(segunda["results"]) == 3


@pytest.mark.parametrize(
    ("consulta", "parametro"),
    [("pagina=5&tamanho=10", "pagina"), ("tamanho=1001", "tamanho"), ("pagina=0", "pagina")],
)
def test_paginacao_invalida(client, serie, consulta, parametro):
    assert parametro in erros(buscar(client, consulta, 400))


def test_sem_resultados_pagina_1_vazia(client, serie):
    assert buscar(client, "indicador=latrocinio") == {
        "count": 0,
        "next": None,
        "previous": None,
        "results": [],
    }


def test_sem_n_mais_1(client, serie, django_assert_max_num_queries):
    with django_assert_max_num_queries(12):
        corpo = buscar(client, "nivel=pais,regiao,uf&unidade=todas&recorte=todos")
    assert corpo["count"] == RegistroAnual.objects.count()


# Detalhe


def test_detalhe_e_igual_ao_item_da_lista(client, serie):
    [item] = buscar(client, "indicador=mvi&uf=BA&ano=2025")["results"]
    resposta = client.get(f"{URL}{item['id']}/")

    assert resposta.status_code == 200
    assert resposta.json() == item
    assert client.get(f"{URL}999999/").status_code == 404
    assert client.get(f"{URL}{item['id']}/?uf=BA").status_code == 400


# /populacao/


def test_populacao_so_ufs_por_padrao(client, serie):
    corpo = client.get("/api/v1/populacao/").json()

    assert corpo["count"] == 4
    assert [(p["localidade"]["codigo"], p["ano"]) for p in corpo["results"]] == [
        ("BA", 2024),
        ("BA", 2025),
        ("SE", 2025),
        ("SP", 2025),
    ]
    assert corpo["results"][0] == {
        "id": corpo["results"][0]["id"],
        "ano": 2024,
        "localidade": {"nivel": "uf", "codigo": "BA", "codigo_ibge": "29", "nome": "Bahia"},
        "valor": "1000000",
        "fonte": {
            "id": serie.fontes["ibge-estimativas"].id,
            "nome": serie.fontes["ibge-estimativas"].nome,
        },
    }


def test_populacao_niveis_ordem_e_filtros(client, serie):
    tudo = client.get("/api/v1/populacao/?nivel=pais,regiao,uf&ordenar=-valor").json()
    assert [p["localidade"]["codigo"] for p in tudo["results"]] == ["BR", "SP", "BA", "BA", "SE"]
    assert client.get("/api/v1/populacao/?uf=BA&ano=2025").json()["count"] == 1


@pytest.mark.parametrize("consulta", ["ordenar=taxa", "indicador=mvi", "regiao=NE", "tamanho=0"])
def test_populacao_parametros_invalidos(client, serie, consulta):
    assert client.get(f"/api/v1/populacao/?{consulta}").status_code == 400
