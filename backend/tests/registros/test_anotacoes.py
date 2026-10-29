"""Taxa, variação, participação e ordenação calculadas no SQL (contrato, 1.1, 1.2, 3 e 4.7.3)."""

from decimal import Decimal

import pytest
from django.db import connection

from apps.importacao.gravacao import carregar_referencias, obter_recortes
from apps.importacao.leitores import fbsp
from apps.importacao.mapeamento import TABELAS
from apps.importacao.processo import importar
from apps.localidades.models import Populacao
from apps.registros.escolhas import Metodo, Situacao, Unidade
from apps.registros.models import RegistroAnual
from apps.registros.queries import anotar_registros, ordenacao
from tests.conftest import TABELAS_REDUZIDAS

pytestmark = pytest.mark.django_db

PM = (("corporacao", "Polícia Militar"), ("situacao_policial", "Em serviço"))
PC = (("corporacao", "Polícia Civil"), ("situacao_policial", "Em serviço"))
VIT, OCO = Unidade.VITIMAS, Unidade.OCORRENCIAS
REGIOES = {"BR", "N", "NE", "S", "CO"}  # os testes não usam "SE", que também é Sergipe


def localidade(refs, local):
    if local in REGIOES:
        return {"regiao": refs.regioes[local]}
    return {"estado": refs.estados[local]}


@pytest.fixture
def base():
    """Registros com resultados conhecidos para cada regra do contrato."""
    refs = carregar_referencias()
    recortes = obter_recortes([PC, PM])
    ibge = refs.fontes["ibge-estimativas"]
    for local, ano, valor in [
        ("BA", 2024, 1_000_000),
        ("BA", 2025, 1_500_000),
        ("NE", 2025, 10_000_000),
        ("BR", 2025, 200_000_000),
    ]:
        Populacao.objects.create(fonte=ibge, ano=ano, valor=valor, **localidade(refs, local))

    def criar(local, indicador, ano, valor, unidade=VIT, recorte=None, taxa=None, **extra):
        situacao = Situacao.NAO_DISPONIVEL if valor is None else Situacao.INFORMADO
        if valor == 0:
            situacao = Situacao.INEXISTENTE
        return RegistroAnual.objects.create(
            **localidade(refs, local),
            indicador=refs.indicadores[indicador],
            recorte=recortes[recorte] if recorte else None,
            fonte=refs.fontes["secretarias-seguranca"],
            ano=ano,
            unidade=unidade,
            valor=None if valor is None else Decimal(valor),
            taxa_publicada=None if taxa is None else Decimal(taxa),
            situacao=situacao,
            origem="T00!A1",
            **extra,
        )

    criar("BA", "mvi", 2012, 50, taxa="3.5")
    criar("BA", "mvi", 2024, 100, taxa="9.9")
    criar("BA", "mvi", 2025, 120, taxa="8.1")
    criar("SP", "mvi", 2025, 50, taxa="8.004")  # sem população: publicada; arredonda para 8.00
    criar("PA", "mvi", 2025, 10, taxa="1.5")
    criar("AC", "mvi", 2025, None)  # "...": taxa nula
    criar("NE", "mvi", 2025, 1000, taxa="9.7")
    criar("N", "mvi", 2025, 900, taxa="4.1")
    criar("BR", "mvi", 2025, 40000, taxa="19.9")
    criar("BA", "homicidio-doloso", 2024, 0, taxa="0")
    criar("BA", "homicidio-doloso", 2025, 60, taxa="4")
    criar("BA", "homicidio-doloso", 2025, 55, unidade=OCO, taxa="3.6")
    criar("BA", "feminicidio", 2025, 3, taxa="0.3")
    criar("NE", "feminicidio", 2025, 30, metodo=Metodo.SOMA_UFS)
    criar("BA", "morte-intervencao-policial", 2025, 30, taxa="2")
    criar("BA", "morte-intervencao-policial", 2025, 12, recorte=PM)
    criar("BA", "morte-intervencao-policial", 2025, None, recorte=PC)
    criar("BA", "roubo", 2025, 500, unidade=OCO, taxa="33")
    criar("BA", "furto-veiculo", 2025, 7, unidade=OCO, taxa="1.2")
    return refs


def um(local="BA", indicador="mvi", ano=2025, unidade=VIT, recorte=None):
    filtro = {"regiao__sigla": local} if local in REGIOES else {"estado__sigla": local}
    registros = anotar_registros().filter(
        indicador__slug=indicador, ano=ano, unidade=unidade, **filtro
    )
    if recorte:
        return registros.get(recorte__chave=";".join(f"{d}={v}" for d, v in recorte))
    return registros.get(recorte__isnull=True)


# Taxa


def test_taxa_calculada_pela_populacao_do_ibge(base):
    registro = um()
    assert (registro.taxa, registro.taxa_origem) == (Decimal(8), "calculada")
    assert registro.populacao == Decimal(1_500_000)
    assert um("NE").taxa == Decimal(10)  # região: população da região
    assert um("BR").taxa == Decimal(20)


def test_taxa_publicada_sem_populacao_ou_em_outra_base(base):
    assert (um(ano=2012).taxa, um(ano=2012).taxa_origem) == (Decimal("3.5"), "publicada")
    assert um("SP").taxa == Decimal("8.004")
    feminicidio = um(indicador="feminicidio")
    assert (feminicidio.taxa, feminicidio.taxa_origem) == (Decimal("0.3"), "publicada")


def test_taxa_nula_sem_valor_ou_sem_denominador(base):
    assert (um("AC").taxa, um("AC").taxa_origem) == (None, None)
    regional = um("NE", "feminicidio")  # soma das UFs, sem população feminina por região
    assert (regional.taxa, regional.taxa_origem) == (None, None)


def test_taxa_em_precisao_total(base):
    Populacao.objects.filter(estado__sigla="BA", ano=2025).update(valor=14_870_907)
    taxa = um().taxa

    assert abs(taxa - Decimal(120) * 100_000 / Decimal(14_870_907)) < Decimal("1e-12")
    assert taxa.as_tuple().exponent < -2  # não arredonda: as 2 casas vêm na serialização


# Variação


def test_variacao_do_valor_e_da_taxa_em_relacao_ao_ano_anterior(base):
    registro = (
        anotar_registros()
        .filter(ano=2025)
        .get(  # filtro por ano não zera a variação
            estado__sigla="BA", indicador__slug="mvi", unidade=VIT
        )
    )
    assert registro.ano_referencia == 2024
    assert registro.variacao_valor_pct == Decimal(20)  # 100 → 120
    assert registro.variacao_taxa_pct == Decimal(-20)  # 10 → 8


@pytest.mark.parametrize(
    ("consulta", "motivo"),
    [
        ({"indicador": "homicidio-doloso"}, "ano anterior com valor zero"),
        ({"indicador": "homicidio-doloso", "unidade": OCO}, "sem ano anterior nessa unidade"),
        ({"local": "SP"}, "sem ano anterior"),
        ({"local": "AC"}, "valor não disponível"),
        ({"indicador": "morte-intervencao-policial", "recorte": PM}, "sem ano anterior no recorte"),
    ],
)
def test_variacao_nula(base, consulta, motivo):
    registro = um(**consulta)
    assert (registro.variacao_valor_pct, registro.variacao_taxa_pct) == (None, None), motivo


# Variação do Brasil em recorte com UFs que não informaram (ADR 0009)


@pytest.fixture
def brasil_parcial():
    """Brasil = soma das UFs que informaram, nos dois anos de cada recorte e no total.

    PM: BA e PA informam nos dois anos; MA não informa em nenhum (mesmo conjunto).
    PC: PA passa a "..." em 2025 (o conjunto muda). Total: PA passa a "..." em 2025.
    """
    refs = carregar_referencias()
    recortes = obter_recortes([PC, PM])

    def criar(local, ano, valor, recorte=None):
        situacao = Situacao.NAO_DISPONIVEL if valor is None else Situacao.INFORMADO
        if valor == 0:
            situacao = Situacao.INEXISTENTE
        RegistroAnual.objects.create(
            **localidade(refs, local),
            indicador=refs.indicadores["morte-intervencao-policial"],
            recorte=recortes[recorte] if recorte else None,
            fonte=refs.fontes["secretarias-seguranca"],
            ano=ano,
            unidade=VIT,
            valor=None if valor is None else Decimal(valor),
            situacao=situacao,
            origem="T00!A1",
        )

    for recorte, valores in {
        PM: {"BA": (40, 50), "PA": (10, 10), "MA": (None, None), "BR": (50, 60)},
        PC: {"BA": (4, 6), "PA": (6, None), "MA": (0, 2), "BR": (10, 8)},
        None: {"BA": (100, 90), "PA": (20, None), "MA": (5, 5), "BR": (125, 95)},
    }.items():
        for local, (em_2024, em_2025) in valores.items():
            criar(local, 2024, em_2024, recorte)
            criar(local, 2025, em_2025, recorte)


def test_variacao_do_brasil_com_o_mesmo_conjunto_de_ufs(brasil_parcial):
    assert um("BR", "morte-intervencao-policial", recorte=PM).variacao_valor_pct == Decimal(20)


def test_variacao_do_brasil_nula_quando_o_conjunto_de_ufs_muda(brasil_parcial):
    brasil = um("BR", "morte-intervencao-policial", recorte=PC)  # PA sai: 10 → 8 não é queda
    assert (brasil.variacao_valor_pct, brasil.variacao_taxa_pct) == (None, None)
    # A regra vale só para o Brasil: a UF que informou nos dois anos mantém a variação.
    assert um("BA", "morte-intervencao-policial", recorte=PC).variacao_valor_pct == Decimal(50)


def test_uf_com_fenomeno_inexistente_conta_como_informada(brasil_parcial):
    # No recorte PC, MA tem "-" (zero) em 2024; com PA também "-" em 2025, as três UFs
    # informaram nos dois anos e o conjunto não muda.
    RegistroAnual.objects.filter(
        estado__sigla="PA", recorte__isnull=False, ano=2025, situacao=Situacao.NAO_DISPONIVEL
    ).update(valor=Decimal(0), situacao=Situacao.INEXISTENTE)
    assert um("BR", "morte-intervencao-policial", recorte=PC).variacao_valor_pct == Decimal(-20)


def test_variacao_nula_quando_uf_passa_a_informar(brasil_parcial):
    RegistroAnual.objects.filter(estado__sigla="MA", recorte__isnull=False, ano=2025).filter(
        situacao=Situacao.NAO_DISPONIVEL
    ).update(valor=Decimal(3), situacao=Situacao.INFORMADO)  # MA entra em 2025 no recorte PM
    assert um("BR", "morte-intervencao-policial", recorte=PM).variacao_valor_pct is None


def test_regra_nao_se_aplica_ao_total_sem_recorte(brasil_parcial):
    assert um("BR", "morte-intervencao-policial").variacao_valor_pct == Decimal(-24)  # 125 → 95


def test_regra_nao_acrescenta_consultas(brasil_parcial, django_assert_num_queries):
    with django_assert_num_queries(1):
        list(anotar_registros())


# Participação


def test_participacao_no_indicador_pai(base):
    homicidio = um(indicador="homicidio-doloso")
    assert (homicidio.participacao_tipo, homicidio.participacao_indicador) == (
        "indicador_pai",
        "mvi",
    )
    assert homicidio.participacao_valor_pct == Decimal(50)  # 60 de 120


def test_participacao_no_total_do_indicador(base):
    recorte = um(indicador="morte-intervencao-policial", recorte=PM)
    assert (recorte.participacao_tipo, recorte.participacao_indicador) == (
        "total_do_indicador",
        "morte-intervencao-policial",
    )
    assert recorte.participacao_valor_pct == Decimal(40)  # 12 de 30
    sem_dado = um(indicador="morte-intervencao-policial", recorte=PC)
    assert (sem_dado.participacao_tipo, sem_dado.participacao_valor_pct) == (
        "total_do_indicador",
        None,
    )


def test_participacao_sem_referencia_em_raiz_e_filho_de_agrupador(base):
    for registro in (
        um(),
        um(indicador="roubo", unidade=OCO),
        um(indicador="furto-veiculo", unidade=OCO),
    ):
        assert (
            registro.participacao_tipo,
            registro.participacao_indicador,
            registro.participacao_valor_pct,
        ) == (None, None, None)


def test_participacao_nula_quando_o_pai_nao_tem_a_unidade(base):
    ocorrencias = um(indicador="homicidio-doloso", unidade=OCO)  # MVI só existe em vítimas
    assert ocorrencias.participacao_tipo == "indicador_pai"
    assert ocorrencias.participacao_valor_pct is None


def test_participacao_com_denominador_zero(base):
    RegistroAnual.objects.filter(estado__sigla="BA", indicador__slug="mvi", ano=2025).update(
        valor=0, situacao=Situacao.INEXISTENTE
    )
    assert um(indicador="homicidio-doloso").participacao_valor_pct is None


def test_uma_consulta_so(base, django_assert_num_queries):
    total = RegistroAnual.objects.count()
    with django_assert_num_queries(1):
        registros = list(anotar_registros())
    assert len(registros) == total


def test_jit_desligado_na_conexao():
    with connection.cursor() as cursor:
        cursor.execute("SHOW jit")
        assert cursor.fetchone()[0] == "off"


# Ordenação


def siglas(registros):
    return [r.estado.sigla if r.estado_id else r.regiao.sigla for r in registros]


def mvi_2025(*pedidos, so_ufs=True):
    registros = anotar_registros().filter(indicador__slug="mvi", ano=2025)
    if so_ufs:
        registros = registros.filter(estado__isnull=False)
    return siglas(registros.select_related("estado", "regiao").order_by(*ordenacao(pedidos)))


def test_ordem_canonica_de_localidades(base):
    assert mvi_2025(so_ufs=False) == ["BR", "N", "NE", "AC", "BA", "PA", "SP"]


def test_ordenar_por_taxa_usa_o_valor_arredondado_e_nulos_ao_final(base):
    # BA 8 e SP 8.004 empatam em "8.00" e ficam na ordem padrão (localidade).
    assert mvi_2025("taxa") == ["PA", "BA", "SP", "AC"]
    assert mvi_2025("-taxa") == ["BA", "SP", "PA", "AC"]


def test_ordenar_por_valor_e_por_varios_campos(base):
    assert mvi_2025("-valor") == ["BA", "SP", "PA", "AC"]
    assert mvi_2025("valor") == ["PA", "SP", "BA", "AC"]


def test_ordem_padrao_indicador_localidade_recorte_unidade_ano(base):
    registros = anotar_registros().filter(estado__sigla="BA").order_by(*ordenacao())
    chaves = [
        (r.indicador.slug, r.recorte_id is not None, r.unidade, r.ano)
        for r in registros.select_related("indicador")
    ]

    assert chaves[:3] == [
        ("mvi", False, VIT, 2012),
        ("mvi", False, VIT, 2024),
        ("mvi", False, VIT, 2025),
    ]
    homicidio = [c for c in chaves if c[0] == "homicidio-doloso"]
    assert homicidio == [
        ("homicidio-doloso", False, VIT, 2024),
        ("homicidio-doloso", False, VIT, 2025),
        ("homicidio-doloso", False, OCO, 2025),
    ]
    mdip = [
        r.recorte.rotulo if r.recorte else None
        for r in registros
        if r.indicador.slug == "morte-intervencao-policial"
    ]
    assert mdip == [None, "Polícia Civil, em serviço", "Polícia Militar, em serviço"]


def test_ordenacao_termina_por_id(base):
    ordem = ordenacao(["-participacao"])
    assert str(ordem[0].expression) == "F(participacao_arredondada)"
    assert ordem[0].descending and ordem[0].nulls_last
    assert str(ordem[-1].expression) == "F(id)"


# Contrato, seção 8: contra a planilha (reduzida)


@pytest.fixture
def importado(planilhas):
    importar(planilhas.dados, planilhas.relatorio, planilhas.manifesto, tabelas=TABELAS_REDUZIDAS)
    return planilhas


def anotados_por_chave():
    """{(sigla, indicador, unidade, ano): registro} dos totais (sem recorte)."""
    registros = (
        anotar_registros()
        .filter(recorte__isnull=True)
        .select_related("estado", "regiao", "indicador")
    )
    return {
        (
            r.estado.sigla if r.estado_id else r.regiao.sigla,
            r.estado_id is not None,
            r.indicador.slug,
            r.unidade,
            r.ano,
        ): r
        for r in registros
    }


def publicados(planilhas, aba, grupo):
    wb = fbsp.abrir(planilhas.planilha)
    tabela = next(t for t in TABELAS if t.aba == aba)
    unidade = {
        "mvi": VIT,
        "morte-intervencao-policial": VIT,
        "homicidio-doloso": VIT,
        "feminicidio": VIT,
        "homicidio-mulheres": VIT,
    }
    base_taxa = dict.fromkeys(unidade, "100 mil habitantes") | {
        "feminicidio": "100 mil mulheres",
        "homicidio-mulheres": "100 mil mulheres",
    }
    lida = fbsp.ler_tabela(wb, tabela, unidade, base_taxa)
    return [p for p in lida.publicados if p.grupo == grupo and p.valor is not None]


def chave_de(publicado):
    c = publicado.chave
    return (c.localidade.sigla, c.localidade.nivel == "uf", c.indicador, c.unidade, c.ano)


@pytest.mark.parametrize("aba", ["T09", "T21"])
def test_participacao_bate_com_as_proporcoes_publicadas(importado, aba):
    registros = anotados_por_chave()
    proporcoes = publicados(importado, aba, "proporcao")

    assert len(proporcoes) == 56  # 28 localidades × 2 anos
    for publicado in proporcoes:
        calculada = registros[chave_de(publicado)].participacao_valor_pct
        assert abs(calculada - publicado.valor) <= Decimal("1e-6"), publicado.origem


def test_variacao_da_taxa_bate_com_a_coluna_publicada(importado):
    registros = anotados_por_chave()
    variacoes = publicados(importado, "T03", "variacao")

    assert len(variacoes) == 56
    for publicado in variacoes:
        calculada = registros[chave_de(publicado)].variacao_taxa_pct
        assert abs(calculada - publicado.valor) <= Decimal("1e-6"), publicado.origem


def test_taxa_calculada_bate_com_a_publicada(importado):
    for registro in anotar_registros().filter(
        taxa_origem="calculada", taxa_publicada__isnull=False
    ):
        assert abs(registro.taxa - registro.taxa_publicada) <= Decimal("1e-6")
