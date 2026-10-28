"""Dados mínimos para os testes da API: referências, uma carga concluída e alguns registros.

Os testes da API não importam a planilha (a importação tem testes próprios); montam aqui só o
necessário para cada recurso responder.
"""

from decimal import Decimal

import pytest
from django.utils import timezone

from apps.importacao.gravacao import carregar_referencias, obter_recortes
from apps.importacao.models import Carga
from apps.registros.escolhas import Situacao, Unidade
from apps.registros.models import RegistroAnual

PM_EM_SERVICO = (("corporacao", "Polícia Militar"), ("situacao_policial", "Em serviço"))


def criar_carga(status=Carga.Status.CONCLUIDA, versao="abc123def456") -> Carga:
    concluida_em = timezone.now() if status == Carga.Status.CONCLUIDA else None
    return Carga.objects.create(
        versao=versao, status=status, concluida_em=concluida_em, total_registros=0
    )


@pytest.fixture
def referencias(db):
    return carregar_referencias()


@pytest.fixture
def dados(referencias):
    """Carga concluída com registros de MVI, homicídio doloso (duas unidades), MDIP e recorte."""
    refs = referencias
    recorte = obter_recortes([PM_EM_SERVICO])[PM_EM_SERVICO]
    fonte = refs.fontes["secretarias-seguranca"]
    ba = refs.estados["BA"]

    def registro(indicador, ano, valor, unidade=Unidade.VITIMAS, recorte=None):
        RegistroAnual.objects.create(
            estado=ba,
            indicador=refs.indicadores[indicador],
            recorte=recorte,
            fonte=fonte,
            ano=ano,
            unidade=unidade,
            valor=Decimal(valor),
            situacao=Situacao.INFORMADO,
            origem="T00!B1",
        )

    registro("mvi", 2012, 100)
    registro("mvi", 2025, 120)
    registro("homicidio-doloso", 2024, 80)
    registro("homicidio-doloso", 2025, 70, unidade=Unidade.OCORRENCIAS)
    registro("morte-intervencao-policial", 2025, 10)
    registro("morte-intervencao-policial", 2025, 6, recorte=recorte)
    criar_carga()
    return refs
