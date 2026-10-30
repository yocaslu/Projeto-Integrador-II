"""Consultas reutilizadas pelos endpoints /registros/, /ranking/ e /comparacao/.

Ficam fora das views para que os cálculos sejam testados sem requisições HTTP. Tudo é calculado
no SQL, por subconsulta e nunca por função de janela (regra 12): um filtro como `ano=2025` não pode
deixar a variação nula por falta do ano anterior na mesma consulta.

`anotar_registros` acrescenta, a cada RegistroAnual (contrato, seção 3):

- `populacao`: população do IBGE da localidade no ano, ou nula.
- `taxa` e `taxa_origem`: `calculada` (valor ÷ população × 100 000, quando a base é 100 mil
  habitantes e há população) ou `publicada` (`taxa_publicada`); as duas nulas sem valor ou sem
  taxa (ex.: total regional de feminicídio, sem população feminina por região).
- `ano_referencia`: `ano - 1`.
- `variacao_valor_pct` e `variacao_taxa_pct`: variação em relação ao ano anterior, na mesma
  localidade, indicador, recorte e unidade; nulas se faltar um dos lados ou se a base for zero. No
  Brasil, em registro com recorte, também nulas quando o conjunto de UFs que informaram o recorte
  muda entre os dois anos (ADR 0009): o total publicado soma só as UFs que informaram, e a
  diferença viria da troca de UFs, não do fenômeno.
- `participacao_tipo`, `participacao_indicador` e `participacao_valor_pct`: parcela no total do
  indicador (registro com recorte) ou no indicador-pai (sem recorte), na mesma localidade, ano e
  unidade; sem referência em raiz e em filho de agrupador.
- `taxa_arredondada`, `variacao_*_arredondada` e `participacao_arredondada`: os mesmos valores a
  2 casas (`ROUND`, meio para longe do zero), só para ordenar: a API classifica pelo que mostra
  (contrato, 1.2).

Os valores anotados têm a precisão do `numeric` do PostgreSQL (divisão com pelo menos 16 dígitos
significativos); o arredondamento para exibição acontece só na serialização (regra 25).
"""

from collections.abc import Iterable
from decimal import Decimal

from django.db.models import (
    BooleanField,
    Case,
    CharField,
    DecimalField,
    Exists,
    ExpressionWrapper,
    F,
    IntegerField,
    OrderBy,
    OuterRef,
    Q,
    QuerySet,
    Subquery,
    Value,
    When,
)
from django.db.models.functions import Coalesce, NullIf, Round

from apps.catalogo.models import BaseTaxa
from apps.localidades.models import Populacao, Regiao
from apps.registros.escolhas import Situacao, Unidade
from apps.registros.models import RegistroAnual

DECIMAL = DecimalField()
CEM = Value(Decimal(100), output_field=DECIMAL)
CEM_MIL = Value(Decimal(100_000), output_field=DECIMAL)
NULO_DECIMAL = Value(None, output_field=DECIMAL)
NULO_TEXTO = Value(None, output_field=CharField())

TAXA_CALCULADA = "calculada"
TAXA_PUBLICADA = "publicada"
PARTICIPACAO_NO_PAI = "indicador_pai"
PARTICIPACAO_NO_TOTAL = "total_do_indicador"


def variacao_percentual(atual: Decimal | None, anterior: Decimal | None) -> Decimal | None:
    """Variação percentual entre dois anos.

    É nula quando falta um dos valores ou quando a base é zero, como define o contrato da API.
    Devolve precisão total: o arredondamento a 2 casas acontece só na serialização
    (apps/api/v1/campos.py; contrato, seção 1.2). É o mesmo cálculo que `anotar_registros` faz no
    SQL, usado aqui pela validação da importação.
    """
    if atual is None or anterior is None or anterior == 0:
        return None
    return (atual - anterior) / anterior * 100


def posicoes_com_empate(valores: list[Decimal | None]) -> list[int | None]:
    """Posições no ranking, em ordem decrescente, com empates na mesma posição (1, 2, 2, 4).

    Valores nulos (dado não disponível) recebem posição nula.
    """
    ordenados = sorted((v for v in valores if v is not None), reverse=True)
    primeira_posicao: dict[Decimal, int] = {}
    for indice, valor in enumerate(ordenados, start=1):
        primeira_posicao.setdefault(valor, indice)
    return [None if v is None else primeira_posicao[v] for v in valores]


# Subconsultas


def _chave(campo: str):
    """Campo anulável comparável por igualdade: nulo vira 0 (os ids começam em 1).

    Em SQL, NULL = NULL não é verdadeiro; a chave única usa NULLS NOT DISTINCT, e as subconsultas
    precisam do mesmo comportamento para estado, regiao e recorte.
    """
    return Coalesce(campo, Value(0))


def _mesma_localidade(registros: QuerySet) -> QuerySet:
    return registros.annotate(_estado=_chave("estado_id"), _regiao=_chave("regiao_id")).filter(
        _estado=_chave(OuterRef("estado_id")), _regiao=_chave(OuterRef("regiao_id"))
    )


def _do_ano_anterior() -> QuerySet:
    """O mesmo registro (localidade, indicador, recorte e unidade) no ano anterior."""
    registros = _mesma_localidade(RegistroAnual.objects.all()).annotate(
        _recorte=_chave("recorte_id")
    )
    return registros.filter(
        _recorte=_chave(OuterRef("recorte_id")),
        indicador_id=OuterRef("indicador_id"),
        unidade=OuterRef("unidade"),
        ano=OuterRef("ano") - 1,
    )


def _conjunto_de_ufs_mudou() -> Case:
    """Verdadeiro no Brasil com recorte quando as UFs que informaram diferem do ano anterior.

    É a diferença simétrica dos dois conjuntos, numa única subconsulta: existe UF que informou o
    mesmo indicador, recorte e unidade em um dos dois anos (o do registro ou o anterior) e não no
    outro. Informar é ter valor: "-" (inexistente, valor 0) conta; "..." (não disponível) não.

    Só o Brasil precisa da regra: a região já fica nula quando alguma UF não informa (regra 4), e o
    total sem recorte publica todas as UFs. O CASE externo faz a subconsulta rodar só nas linhas do
    Brasil com recorte. O Django repete a expressão em cada anotação que a usa, e o custo que fica
    é o do planejamento: por isso uma subconsulta só, e `alias()` em vez de `annotate()` (RNF02).
    """
    ano_externo = OuterRef(OuterRef("ano"))
    informados = RegistroAnual.objects.exclude(situacao=Situacao.NAO_DISPONIVEL)
    no_outro_ano = _mesma_localidade(informados).annotate(_recorte=_chave("recorte_id"))
    no_outro_ano = no_outro_ano.filter(
        _recorte=_chave(OuterRef("recorte_id")),
        indicador_id=OuterRef("indicador_id"),
        unidade=OuterRef("unidade"),
        # o "outro" dos dois anos: ano + (ano - 1) - ano desta linha
        ano=ano_externo * 2 - 1 - OuterRef("ano"),
    )
    so_em_um_ano = informados.filter(
        estado__isnull=False,
        indicador_id=OuterRef("indicador_id"),
        recorte_id=OuterRef("recorte_id"),
        unidade=OuterRef("unidade"),
        ano__in=[OuterRef("ano"), OuterRef("ano") - 1],
    ).filter(~Exists(no_outro_ano))
    return Case(
        When(
            Q(regiao__tipo=Regiao.Tipo.PAIS, recorte__isnull=False) & Exists(so_em_um_ano),
            then=Value(True),
        ),
        default=Value(False),
        output_field=BooleanField(),
    )


def _total_de(indicador_ref: str) -> QuerySet:
    """O registro sem recorte do indicador `indicador_ref`, na mesma localidade, ano e unidade."""
    return _mesma_localidade(RegistroAnual.objects.all()).filter(
        indicador_id=OuterRef(indicador_ref),
        recorte__isnull=True,
        unidade=OuterRef("unidade"),
        ano=OuterRef("ano"),
    )


def _populacao():
    """População do IBGE da localidade do registro no ano (estado ou região, nunca os dois)."""
    do_ano = Populacao.objects.filter(ano=OuterRef("ano"))
    return Coalesce(
        Subquery(do_ano.filter(estado_id=OuterRef("estado_id")).values("valor")[:1]),
        Subquery(do_ano.filter(regiao_id=OuterRef("regiao_id")).values("valor")[:1]),
        output_field=DECIMAL,
    )


def _percentual(numerador, denominador):
    """(numerador ÷ denominador) × 100; nulo se um lado é nulo ou se o denominador é zero."""
    return ExpressionWrapper(numerador * CEM / NullIf(denominador, Value(0)), output_field=DECIMAL)


def _variacao(atual, anterior):
    return ExpressionWrapper(
        (atual - anterior) * CEM / NullIf(anterior, Value(0)), output_field=DECIMAL
    )


def _sem_ufs_trocadas(variacao):
    """A variação, ou nula quando o conjunto de UFs que informaram mudou (ADR 0009)."""
    return Case(When(_ufs_mudaram=True, then=NULO_DECIMAL), default=variacao, output_field=DECIMAL)


def _com_taxa(registros: QuerySet) -> QuerySet:
    """Anota `populacao`, `taxa` e `taxa_origem` (contrato, seção 3, "Taxa")."""
    calculavel = Q(indicador__base_taxa=BaseTaxa.HABITANTES, populacao__isnull=False)
    registros = registros.annotate(populacao=_populacao())
    return registros.annotate(
        taxa=Case(
            When(valor__isnull=True, then=NULO_DECIMAL),
            When(
                calculavel,
                then=ExpressionWrapper(F("valor") * CEM_MIL / F("populacao"), output_field=DECIMAL),
            ),
            default=F("taxa_publicada"),
            output_field=DECIMAL,
        ),
        taxa_origem=Case(
            When(valor__isnull=True, then=NULO_TEXTO),
            When(calculavel, then=Value(TAXA_CALCULADA)),
            When(taxa_publicada__isnull=False, then=Value(TAXA_PUBLICADA)),
            default=NULO_TEXTO,
            output_field=CharField(),
        ),
    )


def anotar_registros(registros: QuerySet | None = None) -> QuerySet:
    """Registros com taxa, variação e participação anotadas (ver a tabela no topo do módulo).

    Tudo numa única consulta, com subconsultas correlacionadas; os filtros do chamador podem vir
    antes ou depois, sem mudar os cálculos.
    """
    registros = _com_taxa(registros if registros is not None else RegistroAnual.objects.all())

    anterior = _do_ano_anterior()
    taxa_anterior = _com_taxa(anterior).values("taxa")[:1]
    registros = registros.annotate(
        ano_referencia=F("ano") - 1,
        _valor_anterior=Subquery(anterior.values("valor")[:1], output_field=DECIMAL),
        _taxa_anterior=Subquery(taxa_anterior, output_field=DECIMAL),
        _total_do_indicador=Subquery(
            _total_de("indicador_id").values("valor")[:1], output_field=DECIMAL
        ),
        _total_do_pai=Subquery(
            _total_de("indicador__indicador_pai_id").values("valor")[:1], output_field=DECIMAL
        ),
        # Pai agrupador (furto) não tem registros: a participação não tem referência.
        _pai_com_registros=Exists(
            RegistroAnual.objects.filter(indicador_id=OuterRef("indicador__indicador_pai_id"))
        ),
    )
    # alias: usada só dentro das variações, não vira coluna do SELECT (ver _conjunto_de_ufs_mudou)
    registros = registros.alias(_ufs_mudaram=_conjunto_de_ufs_mudou())

    com_recorte = Q(recorte__isnull=False)
    no_pai = Q(recorte__isnull=True, _pai_com_registros=True)
    registros = registros.annotate(
        variacao_valor_pct=_sem_ufs_trocadas(_variacao(F("valor"), F("_valor_anterior"))),
        variacao_taxa_pct=_sem_ufs_trocadas(_variacao(F("taxa"), F("_taxa_anterior"))),
        participacao_tipo=Case(
            When(com_recorte, then=Value(PARTICIPACAO_NO_TOTAL)),
            When(no_pai, then=Value(PARTICIPACAO_NO_PAI)),
            default=NULO_TEXTO,
            output_field=CharField(),
        ),
        participacao_indicador=Case(
            When(com_recorte, then=F("indicador__slug")),
            When(no_pai, then=F("indicador__indicador_pai__slug")),
            default=NULO_TEXTO,
            output_field=CharField(),
        ),
        participacao_valor_pct=Case(
            When(com_recorte, then=_percentual(F("valor"), F("_total_do_indicador"))),
            When(no_pai, then=_percentual(F("valor"), F("_total_do_pai"))),
            default=NULO_DECIMAL,
            output_field=DECIMAL,
        ),
    )
    return registros.annotate(
        taxa_arredondada=Round("taxa", 2),
        variacao_valor_arredondada=Round("variacao_valor_pct", 2),
        variacao_taxa_arredondada=Round("variacao_taxa_pct", 2),
        participacao_arredondada=Round("participacao_valor_pct", 2),
    )


# Ordenação (contrato, seções 1.1 e 4.7.3)


def ordem_canonica_localidade(prefixo: str = "") -> list:
    """Brasil; regiões por código do IBGE (N, NE, SE, S, CO); UFs por sigla.

    Serve para qualquer modelo com os campos `estado` e `regiao` (registros, população);
    `prefixo` permite ordenar por uma relação (ex.: "registro__").
    """
    estado, regiao = f"{prefixo}estado", f"{prefixo}regiao"
    nivel = Case(
        When(**{f"{regiao}__tipo": Regiao.Tipo.PAIS}, then=Value(0)),
        When(**{f"{estado}__isnull": True}, then=Value(1)),
        default=Value(2),
        output_field=IntegerField(),
    )
    codigo = Case(
        When(**{f"{estado}__isnull": True}, then=F(f"{regiao}__codigo_ibge")),
        default=F(f"{estado}__sigla"),
        output_field=CharField(),
    )
    return [nivel, codigo]


CAMPOS_DE_ORDENACAO = {
    "ano": lambda: [F("ano")],
    "indicador": lambda: [F("indicador__ordem")],
    "localidade": ordem_canonica_localidade,
    "recorte": lambda: [  # total primeiro, depois por chave
        Case(
            When(recorte__isnull=True, then=Value(0)), default=Value(1), output_field=IntegerField()
        ),
        F("recorte__chave"),
    ],
    "unidade": lambda: [  # vítimas antes de ocorrências
        Case(
            When(unidade=Unidade.VITIMAS, then=Value(0)),
            default=Value(1),
            output_field=IntegerField(),
        )
    ],
    "valor": lambda: [F("valor")],
    "taxa": lambda: [F("taxa_arredondada")],
    "variacao_valor": lambda: [F("variacao_valor_arredondada")],
    "variacao_taxa": lambda: [F("variacao_taxa_arredondada")],
    "participacao": lambda: [F("participacao_arredondada")],
}
"""Nomes aceitos em `ordenar` (contrato, 4.7.3) e as expressões de cada um."""

ORDEM_PADRAO = ("indicador", "localidade", "recorte", "unidade", "ano")

CAMPOS_DE_ORDENACAO_DA_POPULACAO = {
    "ano": CAMPOS_DE_ORDENACAO["ano"],
    "localidade": ordem_canonica_localidade,
    "valor": CAMPOS_DE_ORDENACAO["valor"],
}
"""Nomes aceitos em `ordenar` de /populacao/ (contrato, 4.6)."""

ORDEM_PADRAO_DA_POPULACAO = ("localidade", "ano")


def ordenacao(
    pedidos: Iterable[str] = (),
    campos: dict = CAMPOS_DE_ORDENACAO,
    padrao: tuple[str, ...] = ORDEM_PADRAO,
) -> list[OrderBy]:
    """Critérios pedidos, depois a ordem padrão, depois `id`: ordem total e determinística.

    Prefixo `-` inverte; nulos ficam sempre ao final, nas duas direções (contrato, 4.7.3). Taxa,
    variação e participação usam o valor arredondado a 2 casas (contrato, 1.2). Requer
    `anotar_registros` para os campos calculados. Campos já validados por quem chama.
    """
    pedidos = list(pedidos)
    nomes = {pedido.removeprefix("-") for pedido in pedidos}
    criterios = pedidos + [campo for campo in padrao if campo not in nomes]
    ordem: list[OrderBy] = []
    for criterio in criterios:
        decrescente = criterio.startswith("-")
        for expressao in campos[criterio.removeprefix("-")]():
            ordem.append(
                expressao.desc(nulls_last=True) if decrescente else expressao.asc(nulls_last=True)
            )
    ordem.append(F("id").asc())
    return ordem


# Ranking e comparação (contrato, seções 4.8 e 4.9)

CRITERIOS_DO_RANKING = {
    "taxa": "taxa_arredondada",
    "valor": "valor",
    "participacao": "participacao_arredondada",
}
"""Critério de /ranking/ e a anotação classificada: a API classifica pelo que mostra (1.2)."""


def ranking(
    indicador_id: int, ano: int, unidade: str, recorte_id: int | None, criterio: str
) -> list[tuple[int | None, RegistroAnual]]:
    """As UFs em ordem decrescente do critério, com a posição de cada uma.

    Empates têm a mesma posição e a seguinte salta (1, 2, 2, 4) e se desempatam por sigla; UF com
    o critério nulo vem ao final, com posição nula, por sigla. Brasil e regiões não entram.
    """
    campo = CRITERIOS_DO_RANKING[criterio]
    registros = anotar_registros(
        RegistroAnual.objects.filter(
            estado__isnull=False,
            indicador_id=indicador_id,
            ano=ano,
            unidade=unidade,
            recorte_id=recorte_id,
        )
    ).order_by(F(campo).desc(nulls_last=True), "estado__sigla")
    lista = list(registros.select_related("estado", "indicador", "indicador__fonte_taxa", "fonte"))
    posicoes = posicoes_com_empate([getattr(registro, campo) for registro in lista])
    return list(zip(posicoes, lista, strict=True))


def comparacao(
    estado, indicador_id: int, unidade: str, recorte_id: int | None, ano_min: int, ano_max: int
) -> list[tuple[object, list[RegistroAnual]]]:
    """Três séries, nesta ordem: a UF, a região dela e o Brasil, cada uma por ano crescente.

    Devolve (localidade, registros anotados) por série; a localidade é o Estado ou a Regiao.
    """
    do_indicador = RegistroAnual.objects.filter(
        indicador_id=indicador_id,
        unidade=unidade,
        recorte_id=recorte_id,
        ano__gte=ano_min,
        ano__lte=ano_max,
    )
    brasil = Regiao.objects.get(tipo=Regiao.Tipo.PAIS)
    series = []
    for localidade, filtro in (
        (estado, Q(estado=estado)),
        (estado.regiao, Q(regiao=estado.regiao)),
        (brasil, Q(regiao=brasil)),
    ):
        registros = anotar_registros(do_indicador.filter(filtro)).order_by("ano")
        registros = registros.select_related(
            "estado", "regiao", "indicador", "indicador__fonte_taxa", "fonte"
        )
        series.append((localidade, list(registros)))
    return series
