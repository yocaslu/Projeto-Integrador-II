"""Catálogos: /regioes/, /estados/, /fontes/, /indicadores/ e /recortes/ (contrato, 4.1–4.5)."""

import pytest

from apps.importacao.models import Carga
from tests.api.conftest import criar_carga

LISTAS = [
    "/api/v1/regioes/",
    "/api/v1/estados/",
    "/api/v1/fontes/",
    "/api/v1/indicadores/",
    "/api/v1/recortes/",
]
DETALHES = ["/api/v1/regioes/NE/", "/api/v1/estados/BA/", "/api/v1/indicadores/mvi/"]
RECURSOS = LISTAS + DETALHES + ["/api/v1/metadados/"]  # recursos sem CSV


# Regras comuns (contrato, seções 2, 5.1, 6 e 7.1)


@pytest.mark.parametrize("url", RECURSOS)
def test_sem_carga_concluida_responde_503(client, referencias, url):
    resposta = client.get(url)

    assert resposta.status_code == 503
    assert resposta["Content-Type"].startswith("application/problem+json")
    assert resposta["Cache-Control"] == "no-store"
    assert not resposta.has_header("ETag")
    assert resposta.json()["title"] == "Serviço indisponível"


@pytest.mark.parametrize("status", [Carga.Status.EM_ANDAMENTO, Carga.Status.FALHOU])
def test_carga_nao_concluida_nao_conta(client, referencias, status):
    criar_carga(status)
    assert client.get("/api/v1/regioes/").status_code == 503


@pytest.mark.django_db
@pytest.mark.parametrize("url", ["/api/v1/schema/", "/api/v1/docs/", "/api/v1/redoc/"])
def test_documentacao_nao_depende_da_carga(client, url):
    assert client.get(url).status_code == 200


@pytest.mark.parametrize("url", RECURSOS)
def test_metodo_de_escrita_vem_antes_do_503(client, referencias, url):
    resposta = client.post(url)
    assert resposta.status_code == 405
    assert resposta["Allow"] == "GET, HEAD, OPTIONS"


@pytest.mark.django_db
def test_formato_invalido_vem_antes_do_503(client):
    assert client.get("/api/v1/regioes/?formato=csv").status_code == 406


@pytest.mark.parametrize("url", RECURSOS)
def test_formato_json_e_vary_accept(client, dados, url):
    resposta = client.get(url, {"formato": "json"})

    assert resposta.status_code == 200
    assert resposta["Content-Type"] == "application/json"
    assert "Accept" in resposta["Vary"]


@pytest.mark.parametrize("url", RECURSOS)
@pytest.mark.parametrize("formato", ["csv", "xml"])
def test_catalogos_nao_tem_csv(client, dados, url, formato):
    resposta = client.get(url, {"formato": formato})

    assert resposta.status_code == 406
    assert resposta["Content-Type"].startswith("application/problem+json")


def test_accept_csv_406_e_formato_prevalece_sobre_accept(client, dados):
    assert client.get("/api/v1/regioes/", HTTP_ACCEPT="text/csv").status_code == 406
    resposta = client.get("/api/v1/regioes/?formato=json", HTTP_ACCEPT="text/csv")
    assert resposta.status_code == 200


@pytest.mark.parametrize("url", RECURSOS)
@pytest.mark.parametrize(
    ("consulta", "parametro"),
    [
        ("desconhecido=1", "desconhecido"),
        ("pagina=2", "pagina"),
        ("tamanho=10", "tamanho"),
        ("formato=json&formato=json", "formato"),
        ("formato=", "formato"),
    ],
)
def test_parametro_invalido_400(client, dados, url, consulta, parametro):
    resposta = client.get(f"{url}?{consulta}")

    assert resposta.status_code == 400
    assert parametro in [e["parametro"] for e in resposta.json()["erros"]]


@pytest.mark.parametrize("url", LISTAS)
def test_sem_n_mais_1(client, dados, url, django_assert_max_num_queries):
    with django_assert_max_num_queries(5):
        assert client.get(url).status_code == 200


# /regioes/


def test_regioes_em_ordem_canonica(client, dados):
    regioes = client.get("/api/v1/regioes/").json()

    assert [r["sigla"] for r in regioes] == ["BR", "N", "NE", "SE", "S", "CO"]
    brasil, norte = regioes[0], regioes[1]
    assert brasil == {
        "sigla": "BR",
        "nome": "Brasil",
        "tipo": "pais",
        "codigo_ibge": "1",
        "estados": brasil["estados"],
    }
    assert len(brasil["estados"]) == 27
    assert norte["estados"] == ["AC", "AM", "AP", "PA", "RO", "RR", "TO"]


def test_regiao_por_sigla_sem_diferenca_de_caixa(client, dados):
    resposta = client.get("/api/v1/regioes/se/")

    assert resposta.json()["nome"] == "Sudeste"
    assert resposta.json()["estados"] == ["ES", "MG", "RJ", "SP"]
    assert client.get("/api/v1/regioes/XX/").status_code == 404


# /estados/


def test_estados_por_sigla_com_regiao(client, dados):
    estados = client.get("/api/v1/estados/").json()

    assert len(estados) == 27
    assert estados[0] == {
        "sigla": "AC",
        "nome": "Acre",
        "codigo_ibge": "12",
        "regiao": {"sigla": "N", "nome": "Norte"},
    }
    assert [e["sigla"] for e in estados] == sorted(e["sigla"] for e in estados)


def test_estados_filtrados_por_regiao(client, dados):
    estados = client.get("/api/v1/estados/?regiao=co, s").json()
    assert [e["sigla"] for e in estados] == ["DF", "GO", "MS", "MT", "PR", "RS", "SC"]


@pytest.mark.parametrize("consulta", ["regiao=BR", "regiao=XX", "regiao=NE,"])
def test_estados_regiao_invalida_400(client, dados, consulta):
    resposta = client.get(f"/api/v1/estados/?{consulta}")
    assert resposta.status_code == 400
    assert resposta.json()["erros"][0]["parametro"] == "regiao"


def test_estado_detalhe_e_404(client, dados):
    assert client.get("/api/v1/estados/se/").json()["nome"] == "Sergipe"
    assert client.get("/api/v1/estados/XX/").status_code == 404


# /fontes/


def test_fontes_com_ids_fixos(client, dados):
    fontes = client.get("/api/v1/fontes/").json()

    assert [f["slug"] for f in fontes] == [
        "secretarias-seguranca",
        "ibge-estimativas",
        "ibge-projecoes",
        "senatran-frota",
        "bcb-instituicoes",
    ]
    assert set(fontes[1]) == {"id", "slug", "nome", "descricao", "url"}
    assert [f["id"] for f in fontes] == sorted(f["id"] for f in fontes)


# /indicadores/


def test_indicadores_em_pre_ordem(client, dados):
    indicadores = client.get("/api/v1/indicadores/").json()

    assert len(indicadores) == 18
    assert [i["slug"] for i in indicadores[:4]] == [
        "mvi",
        "homicidio-doloso",
        "homicidio-mulheres",
        "feminicidio",
    ]


def test_indicador_com_unidades_anos_e_subtipos(client, dados):
    homicidio = client.get("/api/v1/indicadores/homicidio-doloso/").json()

    assert homicidio == {
        "slug": "homicidio-doloso",
        "nome": "Homicídio doloso",
        "descricao": homicidio["descricao"],
        "unidade_padrao": "vitimas",
        "unidades": ["vitimas", "ocorrencias"],
        "base_taxa": "100 mil habitantes",
        "fonte_taxa": {
            "id": dados.fontes["ibge-estimativas"].id,
            "nome": homicidio["fonte_taxa"]["nome"],
        },
        "indicador_pai": "mvi",
        "subtipos": ["homicidio-mulheres"],
        "possui_registros": True,
        "anos": [2024, 2025],
        "recortes": [],
    }


def test_indicador_com_recorte_e_raiz(client, dados):
    mdip = client.get("/api/v1/indicadores/morte-intervencao-policial/").json()
    mvi = client.get("/api/v1/indicadores/mvi/").json()

    assert mdip["recortes"] == [
        {"id": mdip["recortes"][0]["id"], "rotulo": "Polícia Militar, em serviço"}
    ]
    assert mvi["indicador_pai"] is None
    assert mvi["anos"] == [2012, 2025]
    assert mvi["subtipos"] == [
        "homicidio-doloso",
        "latrocinio",
        "lesao-corporal-seguida-de-morte",
        "morte-intervencao-policial",
    ]


def test_agrupador_e_indicador_sem_registros(client, dados):
    furto = client.get("/api/v1/indicadores/furto/").json()
    feminicidio = client.get("/api/v1/indicadores/feminicidio/").json()

    assert furto["possui_registros"] is False
    assert (furto["unidades"], furto["anos"], furto["base_taxa"], furto["fonte_taxa"]) == (
        [],
        [],
        None,
        None,
    )
    assert furto["subtipos"] == ["furto-veiculo", "furto-celular"]
    assert feminicidio["fonte_taxa"]["nome"] == "IBGE – Projeções da população"
    assert client.get("/api/v1/indicadores/inexistente/").status_code == 404


# /recortes/


def test_recortes_com_itens_e_indicadores(client, dados):
    [recorte] = client.get("/api/v1/recortes/").json()

    assert recorte["rotulo"] == "Polícia Militar, em serviço"
    assert recorte["chave"] == "corporacao=Polícia Militar;situacao_policial=Em serviço"
    assert recorte["itens"] == [
        {"dimensao": "corporacao", "valor": "Polícia Militar"},
        {"dimensao": "situacao_policial", "valor": "Em serviço"},
    ]
    assert recorte["indicadores"] == ["morte-intervencao-policial"]


def test_recortes_filtrados_por_indicador(client, dados):
    assert client.get("/api/v1/recortes/?indicador=mvi").json() == []
    assert len(client.get("/api/v1/recortes/?indicador=mvi,morte-intervencao-policial").json()) == 1
    resposta = client.get("/api/v1/recortes/?indicador=inexistente")
    assert resposta.status_code == 400
    assert resposta.json()["erros"][0]["parametro"] == "indicador"
