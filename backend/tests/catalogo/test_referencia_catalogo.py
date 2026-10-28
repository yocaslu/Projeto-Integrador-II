from apps.catalogo.models import BaseTaxa
from apps.catalogo.referencia import AGRUPADORES, FONTE_DA_BASE, FONTES, INDICADORES


def test_fontes_na_ordem_fixa_do_adr_0005():
    assert [f.slug for f in FONTES] == [
        "secretarias-seguranca",
        "ibge-estimativas",
        "ibge-projecoes",
        "senatran-frota",
        "bcb-instituicoes",
    ]


def test_toda_base_de_taxa_tem_fonte_do_catalogo():
    slugs = {f.slug for f in FONTES}
    assert set(FONTE_DA_BASE) == set(BaseTaxa)
    assert set(FONTE_DA_BASE.values()) <= slugs


def test_slugs_unicos_e_pai_antes_do_filho():
    vistos = set()
    for indicador in INDICADORES:
        assert indicador.slug not in vistos
        assert indicador.pai is None or indicador.pai in vistos
        vistos.add(indicador.slug)


def test_ordem_e_a_pre_ordem_da_hierarquia():
    filhos = {i.slug: [f.slug for f in INDICADORES if f.pai == i.slug] for i in INDICADORES}

    def pre_ordem(slug):
        yield slug
        for filho in filhos[slug]:
            yield from pre_ordem(filho)

    raizes = [i.slug for i in INDICADORES if i.pai is None]
    assert [s for raiz in raizes for s in pre_ordem(raiz)] == [i.slug for i in INDICADORES]


def test_hierarquia_do_contrato():
    pai = {i.slug: i.pai for i in INDICADORES}
    assert pai["feminicidio"] == "homicidio-mulheres"
    assert pai["homicidio-mulheres"] == "homicidio-doloso"
    assert pai["morte-intervencao-policial"] == "mvi"
    assert pai["furto-veiculo"] == "furto"
    assert len(INDICADORES) == 18


def test_so_o_agrupador_nao_tem_base_de_taxa():
    sem_base = {i.slug for i in INDICADORES if i.base_taxa is None}
    assert sem_base == AGRUPADORES == {"furto"}
