"""Constraints do banco (regra 14): valem mesmo sem passar pela importação."""

from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction

from apps.catalogo.models import Indicador
from apps.importacao.gravacao import carregar_referencias
from apps.localidades.models import Populacao
from apps.registros.escolhas import Metodo, Situacao, Unidade
from apps.registros.models import RegistroAnual

pytestmark = pytest.mark.django_db


@pytest.fixture
def refs():
    return carregar_referencias()


def registro(refs, **campos):
    dados = {
        "estado": refs.estados["BA"],
        "regiao": None,
        "indicador": refs.indicadores["mvi"],
        "recorte": None,
        "fonte": refs.fontes["secretarias-seguranca"],
        "ano": 2025,
        "unidade": Unidade.VITIMAS,
        "valor": Decimal(10),
        "situacao": Situacao.INFORMADO,
        "origem": "T02!O20",
    }
    dados.update(campos)
    return RegistroAnual(**dados)


def falha(objeto):
    with pytest.raises(IntegrityError), transaction.atomic():
        objeto.save()


def test_referencias_carregadas(refs):
    assert list(refs.fontes) == [
        "secretarias-seguranca",
        "ibge-estimativas",
        "ibge-projecoes",
        "senatran-frota",
        "bcb-instituicoes",
    ]
    assert len(refs.estados) == 27
    assert refs.estados["SE"].regiao.sigla == "NE"
    feminicidio = refs.indicadores["feminicidio"]
    assert feminicidio.indicador_pai.slug == "homicidio-mulheres"
    assert feminicidio.fonte_taxa.slug == "ibge-projecoes"
    assert refs.indicadores["furto"].fonte_taxa is None


def test_carregar_referencias_duas_vezes_nao_duplica(refs):
    ids = {slug: indicador.id for slug, indicador in refs.indicadores.items()}
    de_novo = carregar_referencias()
    assert {slug: i.id for slug, i in de_novo.indicadores.items()} == ids


def test_localidade_exige_exatamente_um_entre_estado_e_regiao(refs):
    falha(registro(refs, regiao=refs.regioes["NE"]))
    falha(registro(refs, estado=None))


def test_unicidade_com_nulls_not_distinct(refs):
    registro(refs, estado=None, regiao=refs.regioes["NE"]).save()
    falha(registro(refs, estado=None, regiao=refs.regioes["NE"]))  # recorte nulo nos dois
    registro(refs, estado=None, regiao=refs.regioes["NE"], unidade=Unidade.OCORRENCIAS).save()


@pytest.mark.parametrize(
    ("situacao", "valor"),
    [
        (Situacao.INFORMADO, None),
        (Situacao.INEXISTENTE, Decimal(3)),
        (Situacao.NAO_DISPONIVEL, Decimal(0)),
    ],
)
def test_valor_coerente_com_a_situacao(refs, situacao, valor):
    falha(registro(refs, situacao=situacao, valor=valor))


def test_soma_das_ufs_sem_taxa_publicada(refs):
    falha(
        registro(
            refs,
            estado=None,
            regiao=refs.regioes["NE"],
            metodo=Metodo.SOMA_UFS,
            taxa_publicada=Decimal("1.5"),
        )
    )


def test_base_de_taxa_exige_fonte(refs):
    falha(
        Indicador(
            slug="teste",
            nome="Teste",
            unidade_padrao=Unidade.VITIMAS,
            base_taxa="100 mil habitantes",
            ordem=99,
        )
    )


def test_populacao_unica_por_localidade_e_ano(refs):
    fonte = refs.fontes["ibge-estimativas"]
    Populacao.objects.create(regiao=refs.regioes["BR"], fonte=fonte, ano=2025, valor=1)
    falha(Populacao(regiao=refs.regioes["BR"], fonte=fonte, ano=2025, valor=2))
    falha(Populacao(fonte=fonte, ano=2024, valor=2))
