"""Cache HTTP (contrato, seção 7; testes da seção 8). O 503 sem carga está em test_catalogos.py."""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.api.cache import casa, etag
from apps.importacao.models import Carga
from apps.registros.models import RegistroAnual
from tests.api.conftest import criar_carga

VERSAO = "abc123def456"  # a da carga criada por criar_carga()
JSON, CSV = f'W/"{VERSAO}-json"', f'W/"{VERSAO}-csv"'
RECURSOS_JSON = [
    "/api/v1/regioes/",
    "/api/v1/regioes/NE/",
    "/api/v1/estados/",
    "/api/v1/estados/BA/",
    "/api/v1/fontes/",
    "/api/v1/indicadores/",
    "/api/v1/indicadores/mvi/",
    "/api/v1/recortes/",
    "/api/v1/metadados/",
    "/api/v1/registros/",
    "/api/v1/populacao/",
    "/api/v1/ranking/?indicador=mvi",
    "/api/v1/comparacao/?uf=BA&indicador=mvi",
]
RECURSOS_CSV = [
    "/api/v1/registros/?formato=csv",
    "/api/v1/populacao/?formato=csv",
    "/api/v1/ranking/?indicador=mvi&formato=csv",
    "/api/v1/comparacao/?uf=BA&indicador=mvi&formato=csv",
]


def corpo(resposta) -> bytes:
    return b"".join(resposta.streaming_content) if resposta.streaming else resposta.content


@pytest.mark.parametrize("url", RECURSOS_JSON)
def test_cabecalhos_de_cache_em_todo_200(client, serie, url):
    resposta = client.get(url)

    assert resposta.status_code == 200
    assert resposta["Cache-Control"] == "public, max-age=86400"
    assert resposta["ETag"] == JSON
    assert "Accept" in resposta["Vary"]


@pytest.mark.parametrize("url", RECURSOS_CSV)
def test_etag_do_csv_difere_do_json(client, serie, url):
    resposta = client.get(url)

    assert resposta["ETag"] == CSV
    assert resposta["Cache-Control"] == "public, max-age=86400"
    assert "Accept" in resposta["Vary"]
    assert client.get(url, HTTP_ACCEPT="text/csv")["ETag"] == CSV


def test_registro_detalhe_tem_cache(client, serie):
    id_ = RegistroAnual.objects.values_list("id", flat=True)[0]
    assert client.get(f"/api/v1/registros/{id_}/")["ETag"] == JSON


@pytest.mark.parametrize("url", RECURSOS_JSON[:3] + RECURSOS_JSON[-4:])
def test_304_com_o_etag_atual(client, serie, url):
    resposta = client.get(url, HTTP_IF_NONE_MATCH=JSON)

    assert resposta.status_code == 304
    assert corpo(resposta) == b""
    assert resposta["ETag"] == JSON
    assert resposta["Cache-Control"] == "public, max-age=86400"
    assert "Accept" in resposta["Vary"]


@pytest.mark.parametrize("url", RECURSOS_CSV)
def test_304_no_csv_so_com_o_etag_do_csv(client, serie, url):
    assert client.get(url, HTTP_IF_NONE_MATCH=JSON).status_code == 200
    nao_modificada = client.get(url, HTTP_IF_NONE_MATCH=CSV)
    assert nao_modificada.status_code == 304
    assert corpo(nao_modificada) == b""


@pytest.mark.parametrize(
    "if_none_match",
    [
        JSON,
        f'"{VERSAO}-json"',  # forma forte: a comparação é fraca
        f'"outro", {JSON}',
        "*",
    ],
)
def test_formas_de_if_none_match_que_casam(client, serie, if_none_match):
    assert client.get("/api/v1/regioes/", HTTP_IF_NONE_MATCH=if_none_match).status_code == 304


@pytest.mark.parametrize("if_none_match", ['W/"versaoantiga-json"', CSV, '"lixo'])
def test_etag_diferente_responde_200(client, serie, if_none_match):
    assert client.get("/api/v1/regioes/", HTTP_IF_NONE_MATCH=if_none_match).status_code == 200


def test_nova_carga_muda_o_etag(client, serie):
    nova = criar_carga(versao="fedcba987654")
    Carga.objects.filter(pk=nova.pk).update(concluida_em=timezone.now() + timedelta(hours=1))

    resposta = client.get("/api/v1/regioes/", HTTP_IF_NONE_MATCH=JSON)

    assert resposta.status_code == 200
    assert resposta["ETag"] == 'W/"fedcba987654-json"'


@pytest.mark.parametrize("status", [Carga.Status.EM_ANDAMENTO, Carga.Status.FALHOU])
def test_carga_nao_concluida_nao_muda_o_etag(client, serie, status):
    criar_carga(status, versao="naocontaaaaa")
    assert client.get("/api/v1/regioes/")["ETag"] == JSON


@pytest.mark.parametrize(
    ("url", "status"),
    [
        ("/api/v1/registros/?uf=XX", 400),
        ("/api/v1/estados/XX/", 404),
        ("/api/v1/regioes/?formato=csv", 406),
    ],
)
def test_erros_sem_cache_publico_nem_etag(client, serie, url, status):
    resposta = client.get(url, HTTP_IF_NONE_MATCH=JSON)  # o ETag não transforma erro em 304

    assert resposta.status_code == status
    assert "public" not in resposta.get("Cache-Control", "")
    assert not resposta.has_header("ETag")


def test_metodo_de_escrita_sem_cache(client, serie):
    resposta = client.post("/api/v1/regioes/")
    assert resposta.status_code == 405
    assert not resposta.has_header("ETag")


def test_head_tem_os_mesmos_cabecalhos(client, serie):
    resposta = client.head("/api/v1/registros/")
    assert (resposta.status_code, resposta["ETag"]) == (200, JSON)
    assert client.head("/api/v1/registros/", HTTP_IF_NONE_MATCH=JSON).status_code == 304


def test_options_nao_depende_da_carga(client, referencias):
    resposta = client.options("/api/v1/regioes/")  # sem carga concluída
    assert resposta.status_code == 200
    assert not resposta.has_header("ETag")


def test_funcoes_de_etag():
    assert etag("v1", "csv") == 'W/"v1-csv"'
    assert casa('"v1-csv"', 'W/"v1-csv"')
    assert casa("*", 'W/"v1-csv"')
    assert not casa(None, 'W/"v1-csv"')
    assert not casa('W/"v1-json"', 'W/"v1-csv"')
