"""/ranking/ e /comparacao/ (contrato, seções 4.8 e 4.9; testes da seção 8)."""

from decimal import Decimal

import pytest

from apps.localidades.models import Populacao
from apps.registros.escolhas import Situacao
from apps.registros.models import RegistroAnual

CAMPOS_DO_ITEM = [
    "posicao",
    "localidade",
    "valor",
    "situacao",
    "metodo",
    "taxa",
    "variacao",
    "participacao",
    "fonte",
    "observacao",
]
CAMPOS_DO_PONTO = ["ano", *CAMPOS_DO_ITEM[2:]]


def buscar(client, recurso, consulta="", status=200):
    resposta = client.get(f"/api/v1/{recurso}/?{consulta}")
    assert resposta.status_code == status, resposta.content
    return resposta.json()


def posicoes(corpo):
    return [(r["posicao"], r["localidade"]["codigo"]) for r in corpo["results"]]


def erros(corpo):
    return {e["parametro"] for e in corpo["erros"]}


# /ranking/


def test_ranking_ecoa_os_padroes_resolvidos(client, serie):
    corpo = buscar(client, "ranking", "indicador=mvi")

    assert {k: corpo[k] for k in ("indicador", "ano", "criterio", "unidade", "recorte")} == {
        "indicador": {
            "slug": "mvi",
            "nome": "Mortes Violentas Intencionais",
            "base_taxa": "100 mil habitantes",
        },
        "ano": 2025,
        "criterio": "taxa",
        "unidade": "vitimas",
        "recorte": None,
    }
    # Só UFs (o Brasil e as regiões da série não entram); taxa decrescente; sem dado ao final.
    assert posicoes(corpo) == [(1, "BA"), (2, "SE"), (3, "SP"), (None, "AC")]
    assert list(corpo["results"][0]) == CAMPOS_DO_ITEM  # sem taxa_publicada, id e ano


def test_empate_no_valor_mesma_posicao_e_salto(client, serie):
    RegistroAnual.objects.filter(estado__sigla="SE", indicador__slug="mvi").update(valor=50)
    pa = RegistroAnual.objects.get(estado__sigla="BA", indicador__slug="mvi", ano=2025)
    pa.pk, pa.estado, pa.valor = None, serie.estados["PA"], Decimal(10)
    pa.save()

    corpo = buscar(client, "ranking", "indicador=mvi&criterio=valor")

    assert posicoes(corpo) == [(1, "BA"), (2, "SE"), (2, "SP"), (4, "PA"), (None, "AC")]


def test_empate_pela_taxa_arredondada(client, serie):
    # Sergipe: 30 ÷ 1 198 083 × 100 000 = 2,50400… → "2.50", o mesmo de São Paulo (2,5).
    Populacao.objects.filter(estado__sigla="SE").update(valor=1_198_083)

    corpo = buscar(client, "ranking", "indicador=mvi")

    assert posicoes(corpo) == [(1, "BA"), (2, "SE"), (2, "SP"), (None, "AC")]
    assert [r["taxa"]["valor"] for r in corpo["results"][1:3]] == ["2.50", "2.50"]


def test_inexistente_entra_na_classificacao(client, serie):
    RegistroAnual.objects.filter(estado__sigla="SP", indicador__slug="mvi").update(
        valor=0, situacao=Situacao.INEXISTENTE
    )
    corpo = buscar(client, "ranking", "indicador=mvi&criterio=valor")
    assert posicoes(corpo) == [(1, "BA"), (2, "SE"), (3, "SP"), (None, "AC")]


def test_ranking_por_participacao_no_pai_e_no_recorte(client, serie):
    homicidio = buscar(client, "ranking", "indicador=homicidio-doloso&criterio=participacao")
    parcelas = [
        (r["localidade"]["codigo"], r["participacao"]["valor_pct"]) for r in homicidio["results"]
    ]
    assert parcelas == [("SP", "80.00"), ("BA", "50.00")]  # 40 de 50 MVI; 60 de 120

    pm = next(
        r["recorte"]
        for r in buscar(client, "registros", "indicador=morte-intervencao-policial&recorte=todos")[
            "results"
        ]
        if r["recorte"] and r["recorte"]["rotulo"].startswith("Polícia Militar")
    )
    recorte = buscar(
        client,
        "ranking",
        f"indicador=morte-intervencao-policial&recorte={pm['id']}&criterio=participacao",
    )
    assert recorte["recorte"] == pm
    assert recorte["results"][0]["participacao"]["valor_pct"] == "40.00"


def test_ano_e_unidade_explicitos(client, serie):
    corpo = buscar(client, "ranking", "indicador=homicidio-doloso&unidade=ocorrencias&ano=2025")
    assert (corpo["unidade"], corpo["ano"]) == ("ocorrencias", 2025)
    assert posicoes(corpo) == [(1, "BA")]


@pytest.mark.parametrize(
    ("consulta", "parametro"),
    [
        ("", "indicador"),
        ("indicador=furto", "indicador"),
        ("indicador=mvi,roubo", "indicador"),
        ("indicador=inexistente", "indicador"),
        ("indicador=mvi&ano=2012", "ano"),
        ("indicador=homicidio-doloso&ano=2024&unidade=ocorrencias", "ano"),
        ("indicador=mvi&unidade=ocorrencias", "unidade"),
        ("indicador=mvi&unidade=todas", "unidade"),
        ("indicador=mvi&recorte=todos", "recorte"),
        ("indicador=mvi&recorte=1,2", "recorte"),
        ("indicador=mvi&recorte=99999", "recorte"),
        ("indicador=mvi&criterio=participacao", "criterio"),
        ("indicador=furto-veiculo&criterio=participacao", "criterio"),
        ("indicador=mvi&criterio=posicao", "criterio"),
        ("indicador=mvi&uf=SP", "uf"),
        ("indicador=mvi&regiao=NE", "regiao"),
        ("indicador=mvi&nivel=uf", "nivel"),
        ("indicador=mvi&ordenar=valor", "ordenar"),
        ("indicador=mvi&pagina=1", "pagina"),
    ],
)
def test_ranking_parametros_invalidos(client, serie, consulta, parametro):
    assert parametro in erros(buscar(client, "ranking", consulta, 400))


def test_recorte_de_outro_indicador(client, serie):
    pm = RegistroAnual.objects.filter(recorte__isnull=False).values_list("recorte_id", flat=True)[0]
    assert "recorte" in erros(buscar(client, "ranking", f"indicador=mvi&recorte={pm}", 400))


def test_ranking_com_as_27_ufs(client, importado, django_assert_max_num_queries):
    with django_assert_max_num_queries(12):
        corpo = buscar(
            client, "ranking", "indicador=morte-intervencao-policial&criterio=participacao"
        )

    assert len(corpo["results"]) == 27
    assert {r["localidade"]["nivel"] for r in corpo["results"]} == {"uf"}
    numeros = [Decimal(r["participacao"]["valor_pct"]) for r in corpo["results"]]
    assert numeros == sorted(numeros, reverse=True)
    assert corpo["results"][0]["posicao"] == 1


# /comparacao/


def test_comparacao_tres_series_em_ordem(client, serie):
    corpo = buscar(client, "comparacao", "uf=se&indicador=mvi&ano_min=2025")

    assert {k: corpo[k] for k in ("indicador", "unidade", "recorte", "ano_min", "ano_max")} == {
        "indicador": {
            "slug": "mvi",
            "nome": "Mortes Violentas Intencionais",
            "base_taxa": "100 mil habitantes",
        },
        "unidade": "vitimas",
        "recorte": None,
        "ano_min": 2025,
        "ano_max": 2025,
    }
    assert [s["localidade"] for s in corpo["series"]] == [
        {"nivel": "uf", "codigo": "SE", "codigo_ibge": "28", "nome": "Sergipe"},
        {"nivel": "regiao", "codigo": "NE", "codigo_ibge": "2", "nome": "Nordeste"},
        {"nivel": "pais", "codigo": "BR", "codigo_ibge": "1", "nome": "Brasil"},
    ]
    ponto = corpo["series"][0]["pontos"][0]
    assert list(ponto) == CAMPOS_DO_PONTO  # sem id, localidade, indicador, recorte, unidade
    assert (ponto["ano"], ponto["valor"], ponto["taxa"]["valor"]) == (2025, "30", "3.00")


def test_comparacao_padrao_e_os_anos_do_indicador(client, serie):
    corpo = buscar(client, "comparacao", "uf=BA&indicador=mvi")
    assert (corpo["ano_min"], corpo["ano_max"]) == (2024, 2025)
    assert [p["ano"] for p in corpo["series"][0]["pontos"]] == [2024, 2025]


@pytest.mark.parametrize(
    ("consulta", "parametro"),
    [
        ("indicador=mvi", "uf"),
        ("uf=XX&indicador=mvi", "uf"),
        ("uf=BA,SP&indicador=mvi", "uf"),
        ("uf=BA", "indicador"),
        ("uf=BA&indicador=furto", "indicador"),
        ("uf=BA&indicador=mvi&ano=2025", "ano"),
        ("uf=BA&indicador=mvi&nivel=uf", "nivel"),
        ("uf=BA&indicador=mvi&regiao=NE", "regiao"),
        ("uf=BA&indicador=mvi&ordenar=ano", "ordenar"),
        ("uf=BA&indicador=mvi&ano_min=2025&ano_max=2024", ""),
        ("uf=BA&indicador=feminicidio&ano_min=2024&ano_max=2024", ""),
        ("uf=BA&indicador=mvi&unidade=ocorrencias", "unidade"),
        ("uf=BA&indicador=mvi&recorte=todos", "recorte"),
        ("uf=BA&indicador=mvi&ano_min=2030", "ano_min"),
    ],
)
def test_comparacao_parametros_invalidos(client, serie, consulta, parametro):
    assert parametro in erros(buscar(client, "comparacao", consulta, 400))


def test_comparacao_mesmos_anos_e_regiao_somada_sem_taxa(
    client, importado, django_assert_max_num_queries
):
    with django_assert_max_num_queries(14):
        corpo = buscar(client, "comparacao", "uf=BA&indicador=feminicidio")

    assert [[p["ano"] for p in s["pontos"]] for s in corpo["series"]] == [[2024, 2025]] * 3
    nordeste = corpo["series"][1]["pontos"]
    assert {p["metodo"] for p in nordeste} == {"soma_ufs"}
    assert all(
        p["taxa"] == {"valor": None, "base": "100 mil mulheres", "origem": None, "fonte": None}
        for p in nordeste
    )
    assert corpo["series"][0]["pontos"][0]["taxa"]["origem"] == "publicada"


def test_comparacao_da_serie_historica(client, importado):
    corpo = buscar(client, "comparacao", "uf=SE&indicador=mvi&ano_min=2012")

    assert (corpo["ano_min"], corpo["ano_max"]) == (2012, 2025)
    assert [len(s["pontos"]) for s in corpo["series"]] == [14, 14, 14]
    assert corpo["series"][1]["localidade"]["codigo"] == "NE"  # Sergipe fica no Nordeste
    assert corpo["series"][1]["pontos"][0]["metodo"] == "publicado"  # a T02 publica as regiões
