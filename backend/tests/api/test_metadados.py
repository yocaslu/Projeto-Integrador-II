"""/metadados/ (contrato, seção 4.10). As regras comuns (503, 405, 406, parâmetros) estão em
test_catalogos.py, que inclui este recurso."""

from datetime import timedelta

from django.utils import timezone

from apps.importacao.models import Carga
from tests.api.conftest import criar_carga


def metadados(client):
    resposta = client.get("/api/v1/metadados/")
    assert resposta.status_code == 200, resposta.content
    return resposta.json()


def nos(arvore):
    for no in arvore:
        yield no
        yield from nos(no["subtipos"])


def test_campos_e_listas_fixas(client, dados):
    corpo = metadados(client)

    assert list(corpo) == [
        "carga",
        "anos",
        "niveis",
        "unidades",
        "situacoes",
        "metodos",
        "fontes",
        "indicadores",
    ]
    assert corpo["anos"] == {"min": 2012, "max": 2025}
    assert corpo["niveis"] == ["pais", "regiao", "uf"]
    assert corpo["unidades"] == [
        {"codigo": "vitimas", "nome": "Número de vítimas"},
        {"codigo": "ocorrencias", "nome": "Número de ocorrências"},
    ]
    assert corpo["situacoes"] == [
        {"codigo": "informado", "nome": "Informado"},
        {"codigo": "inexistente", "nome": "Fenômeno inexistente"},
        {"codigo": "nao_disponivel", "nome": "Informação não disponível"},
    ]
    assert corpo["metodos"] == [
        {"codigo": "publicado", "nome": "Publicado pelo FBSP"},
        {"codigo": "soma_ufs", "nome": "Calculado pelo projeto como soma das UFs"},
    ]
    assert [f["slug"] for f in corpo["fontes"]] == [
        "secretarias-seguranca",
        "ibge-estimativas",
        "ibge-projecoes",
        "senatran-frota",
        "bcb-instituicoes",
    ]
    assert set(corpo["fontes"][0]) == {"id", "slug", "nome"}


def test_carga_atual(client, dados):
    atual = Carga.objects.atual()
    atual.arquivos = [{"nome": "anuario-2026.xlsx", "sha256": "6b01f4ed"}]
    atual.total_registros = 1980
    atual.save()
    criar_carga(Carga.Status.FALHOU, versao="falhou00000")  # mais recente, mas não conta

    carga = metadados(client)["carga"]

    assert carga["versao"] == atual.versao
    assert carga["total_registros"] == 1980
    assert carga["arquivos"] == [{"nome": "anuario-2026.xlsx", "sha256": "6b01f4ed"}]
    assert carga["concluida_em"].endswith("-03:00")  # America/Sao_Paulo


def test_carga_concluida_mais_recente(client, dados):
    nova = criar_carga(versao="nova0000000a")
    Carga.objects.filter(pk=nova.pk).update(concluida_em=timezone.now() + timedelta(hours=1))
    assert metadados(client)["carga"]["versao"] == "nova0000000a"


def test_arvore_de_indicadores(client, dados):
    arvore = metadados(client)["indicadores"]
    por_slug = {no["slug"]: no for no in nos(arvore)}

    assert [no["slug"] for no in arvore] == ["mvi", "roubo", "furto"]  # raízes por ordem
    assert len(por_slug) == 18
    homicidio = arvore[0]["subtipos"][0]
    assert homicidio["slug"] == "homicidio-doloso"
    assert homicidio["subtipos"][0]["subtipos"][0]["slug"] == "feminicidio"
    assert [no["slug"] for no in por_slug["furto"]["subtipos"]] == [
        "furto-veiculo",
        "furto-celular",
    ]
    assert list(arvore[0]) == [
        "slug",
        "nome",
        "unidade_padrao",
        "unidades",
        "base_taxa",
        "fonte_taxa",
        "possui_registros",
        "anos",
        "recortes",
        "subtipos",
    ]


def test_unidades_anos_e_recortes_de_cada_indicador(client, dados):
    por_slug = {no["slug"]: no for no in nos(metadados(client)["indicadores"])}

    assert por_slug["mvi"]["anos"] == [2012, 2025]
    assert por_slug["homicidio-doloso"]["unidades"] == ["vitimas", "ocorrencias"]
    assert [r["rotulo"] for r in por_slug["morte-intervencao-policial"]["recortes"]] == [
        "Polícia Militar, em serviço"
    ]
    furto = por_slug["furto"]
    assert (furto["possui_registros"], furto["unidades"], furto["anos"], furto["fonte_taxa"]) == (
        False,
        [],
        [],
        None,
    )
    assert por_slug["feminicidio"]["fonte_taxa"]["nome"] == "IBGE – Projeções da população"


def test_poucas_consultas(client, dados, django_assert_max_num_queries):
    with django_assert_max_num_queries(10):
        metadados(client)
