"""Dados mínimos para os testes da API: referências, uma carga concluída e alguns registros.

Os testes da API não importam a planilha (a importação tem testes próprios); montam aqui só o
necessário para cada recurso responder.
"""

from decimal import Decimal

import pytest
from django.utils import timezone

from apps.importacao.gravacao import carregar_referencias, obter_recortes
from apps.importacao.models import Carga
from apps.localidades.models import Populacao
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


PC_EM_SERVICO = (("corporacao", "Polícia Civil"), ("situacao_policial", "Em serviço"))
REGIOES = {"BR", "N", "NE", "S", "CO"}


@pytest.fixture
def serie(referencias):
    """Carga concluída com registros e populações de resultado conhecido para /registros/.

    "SE" é Sergipe nos registros de UF; o Sudeste entra como ("regiao", "SE").
    """
    refs = referencias
    recortes = obter_recortes([PC_EM_SERVICO, PM_EM_SERVICO])
    fontes = refs.fontes

    def local(nivel, sigla):
        if nivel == "uf":
            return {"estado": refs.estados[sigla]}
        return {"regiao": refs.regioes[sigla]}

    for nivel, sigla, ano, valor in [
        ("uf", "BA", 2024, 1_000_000),
        ("uf", "BA", 2025, 1_500_000),
        ("uf", "SE", 2025, 1_000_000),
        ("uf", "SP", 2025, 2_000_000),
        ("pais", "BR", 2025, 200_000_000),
    ]:
        Populacao.objects.create(
            fonte=fontes["ibge-estimativas"], ano=ano, valor=valor, **local(nivel, sigla)
        )

    def criar(
        nivel, sigla, indicador, ano, valor, unidade=Unidade.VITIMAS, recorte=None, taxa=None
    ):
        if valor is None:
            situacao = Situacao.NAO_DISPONIVEL
        elif valor == 0:
            situacao = Situacao.INEXISTENTE
        else:
            situacao = Situacao.INFORMADO
        return RegistroAnual.objects.create(
            **local(nivel, sigla),
            indicador=refs.indicadores[indicador],
            recorte=recortes[recorte] if recorte else None,
            fonte=fontes["secretarias-seguranca"],
            ano=ano,
            unidade=unidade,
            valor=None if valor is None else Decimal(valor),
            taxa_publicada=None if taxa is None else Decimal(taxa),
            situacao=situacao,
            origem="T00!B1",
        )

    oco = Unidade.OCORRENCIAS
    criar("pais", "BR", "mvi", 2025, 400, taxa="0.2")
    criar("regiao", "NE", "mvi", 2025, 200, taxa="0.5")
    criar("regiao", "SE", "mvi", 2025, 150, taxa="0.4")
    criar("uf", "BA", "mvi", 2024, 100, taxa="10.004")
    criar("uf", "BA", "mvi", 2025, 120, taxa="8.000000000123")
    criar("uf", "SE", "mvi", 2025, 30, taxa="3")
    criar("uf", "SP", "mvi", 2025, 50, taxa="2.5")
    criar("uf", "AC", "mvi", 2025, None)
    criar("uf", "BA", "homicidio-doloso", 2025, 60, taxa="4")
    criar("uf", "BA", "homicidio-doloso", 2025, 55, unidade=oco, taxa="3.7")
    criar("uf", "SP", "homicidio-doloso", 2025, 40, taxa="2")
    criar("uf", "BA", "homicidio-mulheres", 2025, 10, taxa="1.3")
    criar("uf", "BA", "feminicidio", 2025, 3, taxa="0.4")
    criar("uf", "BA", "morte-intervencao-policial", 2025, 30, taxa="2")
    criar("uf", "BA", "morte-intervencao-policial", 2025, 12, recorte=PM_EM_SERVICO)
    criar("uf", "BA", "morte-intervencao-policial", 2025, None, recorte=PC_EM_SERVICO)
    criar("uf", "BA", "roubo", 2025, 500, unidade=oco, taxa="33")
    criar("uf", "BA", "furto-veiculo", 2025, 7, unidade=oco, taxa="1.2")
    criar("uf", "BA", "furto-celular", 2025, 9, unidade=oco, taxa="0.6")
    criar_carga()
    return refs
