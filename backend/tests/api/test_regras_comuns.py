"""Regras comuns a todos os recursos e fonte da taxa por base (contrato, 2, 3 e 5.1; seção 8).

test_catalogos.py cobre os catálogos e /metadados/ em detalhe; aqui as mesmas regras valem para
todos os 14 recursos, inclusive os de consulta e os detalhes.
"""

import pytest

from apps.registros.models import RegistroAnual

RECURSOS = [
    "/api/v1/regioes/",
    "/api/v1/regioes/NE/",
    "/api/v1/estados/",
    "/api/v1/estados/BA/",
    "/api/v1/indicadores/",
    "/api/v1/indicadores/mvi/",
    "/api/v1/recortes/",
    "/api/v1/fontes/",
    "/api/v1/metadados/",
    "/api/v1/registros/",
    "/api/v1/registros/{id}/",
    "/api/v1/populacao/",
    "/api/v1/ranking/?indicador=mvi",
    "/api/v1/comparacao/?uf=BA&indicador=mvi",
]


def url_de(serie, recurso: str, consulta: str = "") -> str:
    recurso = recurso.format(id=RegistroAnual.objects.values_list("id", flat=True)[0])
    if not consulta:
        return recurso
    return f"{recurso}{'&' if '?' in recurso else '?'}{consulta}"


@pytest.mark.parametrize("recurso", RECURSOS)
@pytest.mark.parametrize(
    ("consulta", "parametro"),
    [
        ("desconhecido=1", "desconhecido"),
        ("formato=json&formato=json", "formato"),
        ("formato=", "formato"),
    ],
)
def test_parametro_desconhecido_repetido_ou_vazio(client, serie, recurso, consulta, parametro):
    resposta = client.get(url_de(serie, recurso, consulta))

    assert resposta.status_code == 400
    assert parametro in [e["parametro"] for e in resposta.json()["erros"]]


@pytest.mark.parametrize("recurso", RECURSOS)
def test_formato_json_aceito_e_xml_406(client, serie, recurso):
    assert client.get(url_de(serie, recurso, "formato=json")).status_code == 200
    resposta = client.get(url_de(serie, recurso, "formato=xml"))
    assert resposta.status_code == 406
    assert resposta["Content-Type"].startswith("application/problem+json")


def test_fonte_da_taxa_de_cada_base(client, serie):
    """Cada base de taxa tem a fonte da tabela do ADR 0005, no catálogo e nos registros."""
    fontes = serie.fontes
    esperado = {
        "100 mil habitantes": fontes["ibge-estimativas"].nome,
        "100 mil mulheres": fontes["ibge-projecoes"].nome,
        "100 mil veículos": fontes["senatran-frota"].nome,
        "100 instituições": fontes["bcb-instituicoes"].nome,
    }
    for indicador in client.get("/api/v1/indicadores/").json():
        if indicador["base_taxa"] is None:
            assert indicador["fonte_taxa"] is None  # só o agrupador furto
        else:
            assert indicador["fonte_taxa"]["nome"] == esperado[indicador["base_taxa"]]

    consulta = "uf=BA&ano=2025&indicador=mvi,feminicidio,furto-veiculo&unidade=todas"
    for registro in client.get(f"/api/v1/registros/?{consulta}").json()["results"]:
        taxa = registro["taxa"]
        assert taxa["fonte"]["nome"] == esperado[taxa["base"]], registro["indicador"]


def test_fonte_da_taxa_nula_sem_taxa(client, serie):
    [acre] = client.get("/api/v1/registros/?uf=AC&indicador=mvi").json()["results"]
    assert acre["taxa"]["valor"] is None
    assert acre["taxa"]["fonte"] is None
