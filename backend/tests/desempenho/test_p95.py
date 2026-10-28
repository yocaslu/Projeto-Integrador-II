"""RNF02: p95 < 500 ms nas consultas filtradas por UF, ano e indicador (método no ADR 0005).

Fora da execução padrão; rode com `uv run pytest -m desempenho --no-cov`. Mede, em processo, com o
`django.test.Client`: roteamento, middlewares, validação, consultas ao PostgreSQL, serialização e,
no CSV, o consumo completo do streaming. Não mede rede nem Traefik, e não envia `If-None-Match`:
toda requisição monta a resposta.
"""

import statistics
import time
from itertools import product

import pytest

from apps.localidades.referencia import ESTADOS

pytestmark = [pytest.mark.desempenho, pytest.mark.django_db]

UFS = [estado.sigla for estado in ESTADOS]
ANOS = (2024, 2025)
INDICADORES = ("mvi", "homicidio-doloso", "feminicidio", "morte-intervencao-policial", "roubo")
AQUECIMENTO = 20
LIMITE_MS = 500
MAXIMO_DE_CONSULTAS = 15

RECURSOS = {
    "registros": [
        f"/api/v1/registros/?uf={uf}&ano={ano}&indicador={slug}"
        for uf, ano, slug in product(UFS, ANOS, INDICADORES)
    ],
    "registros-csv": [
        f"/api/v1/registros/?uf={uf}&ano={ano}&indicador={slug}&formato=csv"
        for uf, ano, slug in product(UFS, ANOS, INDICADORES)
    ],
    "ranking": [
        f"/api/v1/ranking/?indicador={slug}&ano={ano}"
        for _ in range(3)
        for slug, ano in product(INDICADORES, ANOS)
    ],
    "comparacao": [
        f"/api/v1/comparacao/?uf={uf}&indicador={slug}" for uf, slug in product(UFS, INDICADORES)
    ],
}


def requisitar(client, url) -> float:
    """Milissegundos de uma requisição, com o corpo inteiro consumido; exige 200."""
    inicio = time.perf_counter()
    resposta = client.get(url)
    if resposta.streaming:
        b"".join(resposta.streaming_content)
    else:
        resposta.content  # noqa: B018 o corpo já foi montado; acessá-lo faz parte da medida
    decorrido = (time.perf_counter() - inicio) * 1000
    assert resposta.status_code == 200, (url, resposta.content[:300])
    return decorrido


def test_quantidade_de_requisicoes_do_adr():
    assert {recurso: len(urls) for recurso, urls in RECURSOS.items()} == {
        "registros": 270,
        "registros-csv": 270,
        "ranking": 30,
        "comparacao": 135,
    }


@pytest.mark.parametrize("recurso", list(RECURSOS))
def test_p95_abaixo_de_500_ms(client, carga_real, recurso, django_assert_max_num_queries):
    urls = RECURSOS[recurso]
    for url in urls[:AQUECIMENTO]:
        requisitar(client, url)

    with django_assert_max_num_queries(MAXIMO_DE_CONSULTAS):  # regressão N+1 aparece aqui
        requisitar(client, urls[0])

    tempos = [requisitar(client, url) for url in urls]
    p95 = statistics.quantiles(tempos, n=20, method="inclusive")[18]
    assert p95 < LIMITE_MS, (
        f"{recurso}: p95 = {p95:.0f} ms (limite {LIMITE_MS} ms); "
        f"p50 = {statistics.median(tempos):.0f} ms; máximo = {max(tempos):.0f} ms; "
        f"{len(tempos)} requisições"
    )
