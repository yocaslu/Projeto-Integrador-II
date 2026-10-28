"""Views da versão 1. Todas são somente leitura (APIView com GET; RNF06, regra 15).

`RecursoV1` aplica, em toda view, a ordem de verificação do contrato: método (405), formato (406),
carga concluída (503, seção 7.1) e só então os parâmetros (400, seção 2), lidos por
`LeitorParametros` e validados de uma vez. Toda resposta 200 leva `Vary: Accept` (regra 27).
"""

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from functools import reduce
from operator import or_

from django.db.models import F, Max, Min, Prefetch, Q
from django.http import Http404
from django.utils.cache import patch_vary_headers
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import exceptions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.erros import SemCargaConcluida
from apps.api.paginacao import paginar
from apps.api.v1 import campos
from apps.api.v1 import serializers as s
from apps.api.v1.parametros import NIVEIS, Anos, LeitorParametros, Localidades
from apps.catalogo.models import Fonte, Indicador, Recorte, RecorteItem
from apps.importacao.models import Carga
from apps.localidades.models import Estado, Populacao, Regiao
from apps.registros.escolhas import Metodo, Situacao, Unidade
from apps.registros.models import RegistroAnual
from apps.registros.queries import (
    CAMPOS_DE_ORDENACAO,
    CAMPOS_DE_ORDENACAO_DA_POPULACAO,
    CRITERIOS_DO_RANKING,
    ORDEM_PADRAO_DA_POPULACAO,
    anotar_registros,
    comparacao,
    ordenacao,
    ranking,
)

FORMATO_JSON = OpenApiParameter(
    "formato",
    str,
    enum=["json"],
    description="Formato da resposta. Este recurso só tem JSON; `csv` → 406.",
)


class RecursoV1(APIView):
    http_method_names = ["get", "head", "options"]
    parametros_permitidos: tuple[str, ...] = ()
    paginado = False

    def initial(self, request, *args, **kwargs):
        if request.method.lower() not in self.http_method_names:
            raise exceptions.MethodNotAllowed(request.method)
        super().initial(request, *args, **kwargs)  # negociação de formato (406) e versão
        if request.method in ("GET", "HEAD"):
            self.carga = Carga.objects.atual()
            if self.carga is None:
                raise SemCargaConcluida()
        self.parametros = LeitorParametros(
            request.query_params,
            self.parametros_permitidos,
            paginado=self.paginado,
            csv=getattr(request.accepted_renderer, "format", None) == "csv",
        )

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        if response.status_code == 200:
            patch_vary_headers(response, ["Accept"])
        return response


def _todas_as_ufs() -> list[str]:
    return list(Estado.objects.order_by("sigla").values_list("sigla", flat=True))


def _regioes_com_estados():
    return Regiao.objects.prefetch_related(
        Prefetch("estados", queryset=Estado.objects.order_by("sigla"))
    )


class ListaRegioes(RecursoV1):
    @extend_schema(
        summary="Regiões e Brasil",
        description="As cinco regiões e o total nacional, em ordem canônica (BR, N, NE, SE, S, "
        "CO), com as siglas das UFs de cada uma (contrato, 4.1).",
        parameters=[FORMATO_JSON],
        responses=s.RegiaoSerializer(many=True),
    )
    def get(self, request, version):
        self.parametros.validar()
        contexto = {"todas_as_ufs": _todas_as_ufs()}
        return Response(
            s.RegiaoSerializer(_regioes_com_estados(), many=True, context=contexto).data
        )


class DetalheRegiao(RecursoV1):
    @extend_schema(
        summary="Uma região ou o Brasil",
        description="Sigla sem diferença de caixa; sigla inexistente → 404.",
        parameters=[FORMATO_JSON],
        responses=s.RegiaoSerializer,
    )
    def get(self, request, version, sigla):
        self.parametros.validar()
        regiao = _regioes_com_estados().filter(sigla=sigla.upper()).first()
        if regiao is None:
            raise Http404(f"Região não encontrada: {sigla}.")
        contexto = {"todas_as_ufs": _todas_as_ufs()}
        return Response(s.RegiaoSerializer(regiao, context=contexto).data)


def _estados():
    return Estado.objects.select_related("regiao").order_by("sigla")


class ListaEstados(RecursoV1):
    parametros_permitidos = ("regiao",)

    @extend_schema(
        summary="Unidades da Federação",
        description="As 27 UFs, por sigla, com a região a que pertencem (contrato, 4.2).",
        parameters=[
            OpenApiParameter(
                "regiao",
                str,
                description="Lista de siglas de região separadas por vírgula (N, NE, SE, S, CO). "
                "`BR` → 400.",
            ),
            FORMATO_JSON,
        ],
        responses=s.EstadoSerializer(many=True),
    )
    def get(self, request, version):
        regioes_validas = Regiao.objects.filter(tipo=Regiao.Tipo.REGIAO).values_list(
            "sigla", flat=True
        )
        regioes = self.parametros.lista("regiao", set(regioes_validas), maiusculas=True)
        self.parametros.validar()
        estados = _estados()
        if regioes:
            estados = estados.filter(regiao__sigla__in=regioes)
        return Response(s.EstadoSerializer(estados, many=True).data)


class DetalheEstado(RecursoV1):
    @extend_schema(
        summary="Uma Unidade da Federação",
        description="Sigla sem diferença de caixa; sigla inexistente → 404.",
        parameters=[FORMATO_JSON],
        responses=s.EstadoSerializer,
    )
    def get(self, request, version, uf):
        self.parametros.validar()
        estado = _estados().filter(sigla=uf.upper()).first()
        if estado is None:
            raise Http404(f"UF não encontrada: {uf}.")
        return Response(s.EstadoSerializer(estado).data)


class ListaFontes(RecursoV1):
    @extend_schema(
        summary="Fontes dos dados",
        description="Catálogo fixo de fontes, por id (contrato, 4.5; ADR 0005).",
        parameters=[FORMATO_JSON],
        responses=s.FonteSerializer(many=True),
    )
    def get(self, request, version):
        self.parametros.validar()
        return Response(s.FonteSerializer(Fonte.objects.order_by("id"), many=True).data)


@dataclass
class ResumoDoIndicador:
    unidades: set[str] = field(default_factory=set)
    anos: set[int] = field(default_factory=set)
    recortes: set[int] = field(default_factory=set)


def _contexto_dos_indicadores() -> dict:
    """Unidades, anos e recortes com registros de cada indicador, numa consulta só."""
    resumo: dict[int, ResumoDoIndicador] = defaultdict(ResumoDoIndicador)
    combinacoes = RegistroAnual.objects.values_list(
        "indicador_id", "unidade", "ano", "recorte_id"
    ).distinct()
    for indicador_id, unidade, ano, recorte_id in combinacoes:
        item = resumo[indicador_id]
        item.unidades.add(unidade)
        item.anos.add(ano)
        if recorte_id is not None:
            item.recortes.add(recorte_id)
    subtipos: dict[int, list[str]] = defaultdict(list)
    filhos = Indicador.objects.filter(indicador_pai__isnull=False).order_by("ordem")
    for pai_id, slug in filhos.values_list("indicador_pai_id", "slug"):
        subtipos[pai_id].append(slug)
    return {
        "resumo": dict(resumo),
        "subtipos": dict(subtipos),
        "recortes": {recorte.id: recorte for recorte in Recorte.objects.all()},
    }


def _indicadores():
    return Indicador.objects.select_related("fonte_taxa", "indicador_pai").order_by("ordem")


class ListaIndicadores(RecursoV1):
    @extend_schema(
        summary="Indicadores",
        description="Lista plana, pela ordem da hierarquia (pré-ordem). A hierarquia significa "
        '"contido em", nunca "soma de" (contrato, 4.3). A árvore aninhada está em /metadados/.',
        parameters=[FORMATO_JSON],
        responses=s.IndicadorSerializer(many=True),
    )
    def get(self, request, version):
        self.parametros.validar()
        dados = s.IndicadorSerializer(
            _indicadores(), many=True, context=_contexto_dos_indicadores()
        ).data
        return Response(dados)


class DetalheIndicador(RecursoV1):
    @extend_schema(
        summary="Um indicador",
        description="Slug inexistente → 404.",
        parameters=[FORMATO_JSON],
        responses=s.IndicadorSerializer,
    )
    def get(self, request, version, slug):
        self.parametros.validar()
        indicador = _indicadores().filter(slug=slug).first()
        if indicador is None:
            raise Http404(f"Indicador não encontrado: {slug}.")
        return Response(s.IndicadorSerializer(indicador, context=_contexto_dos_indicadores()).data)


class ListaRecortes(RecursoV1):
    parametros_permitidos = ("indicador",)

    @extend_schema(
        summary="Recortes",
        description="Recortes de agentes (corporação e situação do policial), por chave, com os "
        "indicadores que têm registros em cada um (contrato, 4.4). O `id` é o que se passa em "
        "`recorte=` nos outros recursos.",
        parameters=[
            OpenApiParameter(
                "indicador",
                str,
                description="Lista de slugs separados por vírgula: só os recortes com registros "
                "desses indicadores.",
            ),
            FORMATO_JSON,
        ],
        responses=s.RecorteSerializer(many=True),
    )
    def get(self, request, version):
        slugs_validos = set(Indicador.objects.values_list("slug", flat=True))
        filtro = self.parametros.lista("indicador", slugs_validos)
        self.parametros.validar()

        indicadores_do_recorte: dict[int, list[str]] = defaultdict(list)
        pares = (
            RegistroAnual.objects.filter(recorte__isnull=False)
            .values_list("recorte_id", "indicador__slug", "indicador__ordem")
            .distinct()
            .order_by("indicador__ordem")
        )
        for recorte_id, slug, _ in pares:
            indicadores_do_recorte[recorte_id].append(slug)

        recortes = Recorte.objects.prefetch_related(
            Prefetch("itens", queryset=RecorteItem.objects.order_by("dimensao"))
        ).order_by("chave")
        if filtro:
            ids = [r for r, slugs in indicadores_do_recorte.items() if set(slugs) & set(filtro)]
            recortes = recortes.filter(id__in=ids)
        contexto = {"indicadores_do_recorte": indicadores_do_recorte}
        return Response(s.RecorteSerializer(recortes, many=True, context=contexto).data)


# Registros e população (contrato, seções 4.6 e 4.7)

PARAMETROS_DE_LOCALIDADE = [
    OpenApiParameter(
        "nivel",
        str,
        description="Lista de `pais`, `regiao`, `uf`. Sem `nivel`, `uf` nem `regiao`: só as "
        "UFs. Misturar níveis só por lista explícita (ex.: `pais,regiao,uf`), e então sem "
        "`uf`/`regiao`.",
    ),
    OpenApiParameter(
        "uf", str, description="Lista de siglas de UF (ex.: `SP,RJ`); implica `nivel=uf`."
    ),
    OpenApiParameter(
        "regiao",
        str,
        description="Lista de siglas de região (N, NE, SE, S, CO); exige `nivel`: com `nivel=uf`, "
        "as UFs da região; com `nivel=regiao`, o agregado. `BR` → 400.",
    ),
]
PARAMETROS_DE_ANOS = [
    OpenApiParameter("ano", str, description="Lista de anos (ex.: `2024,2025`)."),
    OpenApiParameter("ano_min", int, description="Primeiro ano do intervalo fechado."),
    OpenApiParameter("ano_max", int, description="Último ano do intervalo fechado."),
]
PARAMETROS_DE_PAGINA = [
    OpenApiParameter("pagina", int, description="Página, a partir de 1. Além da última → 400."),
    OpenApiParameter("tamanho", int, description="Itens por página: padrão 100, máximo 1000."),
]


def _siglas() -> tuple[set[str], set[str]]:
    """Siglas válidas de UF e de região (sem o Brasil)."""
    ufs = set(Estado.objects.values_list("sigla", flat=True))
    regioes = set(Regiao.objects.filter(tipo=Regiao.Tipo.REGIAO).values_list("sigla", flat=True))
    return ufs, regioes


def _intervalo_de_anos() -> tuple[int, int]:
    """Anos com registros, lidos do banco (contrato, seção 2, regra 8)."""
    limites = RegistroAnual.objects.aggregate(minimo=Min("ano"), maximo=Max("ano"))
    return limites["minimo"], limites["maximo"]


def _filtro_de_localidade(locais: Localidades) -> Q:
    """Filtro da regra de nível (contrato, 4.7.2); `locais` já validado pelo LeitorParametros."""
    por_nivel = {
        "pais": Q(regiao__tipo=Regiao.Tipo.PAIS),
        "regiao": Q(regiao__tipo=Regiao.Tipo.REGIAO),
        "uf": Q(estado__isnull=False),
    }
    filtro = reduce(or_, (por_nivel[nivel] for nivel in locais.niveis))
    if locais.ufs:
        filtro &= Q(estado__sigla__in=locais.ufs)
    if locais.regioes:
        if locais.niveis == ("uf",):
            filtro &= Q(estado__regiao__sigla__in=locais.regioes)
        else:
            filtro &= Q(regiao__sigla__in=locais.regioes)
    return filtro


def _filtro_de_anos(anos: Anos) -> Q:
    filtro = Q()
    if anos.ano:
        filtro &= Q(ano__in=anos.ano)
    if anos.ano_min is not None:
        filtro &= Q(ano__gte=anos.ano_min)
    if anos.ano_max is not None:
        filtro &= Q(ano__lte=anos.ano_max)
    return filtro


def _descendentes(slugs: Iterable[str], filhos: dict[str, list[str]]) -> list[str]:
    """Os indicadores pedidos e todos os seus descendentes, em qualquer profundidade."""
    resultado: list[str] = []
    pendentes = list(slugs)
    while pendentes:
        slug = pendentes.pop(0)
        if slug not in resultado:
            resultado.append(slug)
            pendentes.extend(filhos.get(slug, []))
    return resultado


UNIDADE_PADRAO, UNIDADE_TODAS = "padrao", "todas"
RECORTE_TOTAL, RECORTE_TODOS = "total", "todos"


class ListaRegistros(RecursoV1):
    parametros_permitidos = (
        "nivel",
        "uf",
        "regiao",
        "indicador",
        "incluir_subtipos",
        "ano",
        "ano_min",
        "ano_max",
        "unidade",
        "recorte",
        "situacao",
        "ordenar",
    )
    paginado = True

    @extend_schema(
        operation_id="api_v1_registros_lista",
        summary="Registros",
        description="Tabela de fatos com valor, taxa, variação, participação, situação do dado, "
        "método e fonte (contrato, 4.7). Por padrão, só totais (`recorte=total`), na unidade "
        "padrão de cada indicador (`unidade=padrao`) e só as UFs: vítimas e ocorrências, totais e "
        "recortes, Brasil, regiões e UFs nunca se misturam por omissão.",
        parameters=[
            *PARAMETROS_DE_LOCALIDADE,
            OpenApiParameter(
                "indicador",
                str,
                description="Lista de slugs. Agrupador (`furto`) exige `incluir_subtipos=true`.",
            ),
            OpenApiParameter(
                "incluir_subtipos",
                bool,
                description="`true` inclui todos os descendentes dos indicadores; exige "
                "`indicador`.",
            ),
            *PARAMETROS_DE_ANOS,
            OpenApiParameter(
                "unidade",
                str,
                description="`padrao` (padrão): a unidade padrão de cada indicador; `todas`; ou "
                "lista de `vitimas`, `ocorrencias`.",
            ),
            OpenApiParameter(
                "recorte",
                str,
                description="`total` (padrão): só registros sem recorte; `todos`; ou lista de ids "
                "de /recortes/ (só esses recortes).",
            ),
            OpenApiParameter(
                "situacao",
                str,
                description="Lista de `informado`, `inexistente`, `nao_disponivel`.",
            ),
            OpenApiParameter(
                "ordenar",
                str,
                description="Lista de campos; `-` inverte. Campos: "
                + ", ".join(CAMPOS_DE_ORDENACAO)
                + ". Depois vem a ordem padrão (indicador, localidade, recorte, unidade, ano) e "
                "`id`; nulos sempre ao final.",
            ),
            *PARAMETROS_DE_PAGINA,
            FORMATO_JSON,
        ],
        responses=s.PaginaDeRegistrosSerializer,
    )
    def get(self, request, version):
        p = self.parametros
        ufs, regioes = _siglas()
        locais = p.localidades(ufs, regioes)

        indicadores = list(
            Indicador.objects.order_by("ordem").values_list("slug", "indicador_pai__slug")
        )
        filhos: dict[str, list[str]] = defaultdict(list)
        for slug, pai in indicadores:
            if pai:
                filhos[pai].append(slug)
        slugs = p.lista("indicador", {slug for slug, _ in indicadores})
        subtipos = p.booleano("incluir_subtipos")
        anos = p.anos(_intervalo_de_anos())
        unidades = p.lista("unidade", {UNIDADE_PADRAO, UNIDADE_TODAS, *Unidade.values})
        ids_de_recorte = {str(i) for i in Recorte.objects.values_list("id", flat=True)}
        recortes = p.lista("recorte", {RECORTE_TOTAL, RECORTE_TODOS, *ids_de_recorte})
        situacoes = p.lista("situacao", set(Situacao.values))
        ordem = p.ordenacao(set(CAMPOS_DE_ORDENACAO))
        paginacao = p.paginacao()

        if subtipos and not p.informado("indicador"):
            p.erro("incluir_subtipos", "incluir_subtipos=true exige o parâmetro indicador.")
        if unidades and len(unidades) > 1 and {UNIDADE_PADRAO, UNIDADE_TODAS} & set(unidades):
            p.erro("unidade", "padrao e todas não se misturam com outras unidades.")
        if recortes and len(recortes) > 1 and {RECORTE_TOTAL, RECORTE_TODOS} & set(recortes):
            p.erro("recorte", "total e todos não se misturam com ids de recorte.")

        efetivos = None
        if slugs:
            unidades_com_registros: dict[str, set[str]] = defaultdict(set)
            for slug, unidade in RegistroAnual.objects.values_list(
                "indicador__slug", "unidade"
            ).distinct():
                unidades_com_registros[slug].add(unidade)
            if subtipos:
                efetivos = _descendentes(slugs, filhos)
            else:
                efetivos = list(slugs)
                for slug in slugs:
                    if slug in filhos and not unidades_com_registros[slug]:
                        p.erro(
                            "indicador",
                            f"O indicador {slug} não tem registros próprios; "
                            "use incluir_subtipos=true.",
                        )
            pedidas = set(unidades or ()) - {UNIDADE_PADRAO, UNIDADE_TODAS}
            sem_registros = not any(unidades_com_registros[slug] & pedidas for slug in efetivos)
            if pedidas and p.valido("unidade") and p.valido("indicador") and sem_registros:
                lista = ", ".join(sorted(pedidas))
                if len(efetivos) == 1:
                    mensagem = f"O indicador {efetivos[0]} não tem registros em {lista}."
                else:
                    mensagem = f"Os indicadores {', '.join(efetivos)} não têm registros em {lista}."
                p.erro("unidade", mensagem)
        p.validar()

        filtro = _filtro_de_localidade(locais) & _filtro_de_anos(anos)
        if efetivos:
            filtro &= Q(indicador__slug__in=efetivos)
        if not unidades or unidades == (UNIDADE_PADRAO,):
            filtro &= Q(unidade=F("indicador__unidade_padrao"))
        elif unidades != (UNIDADE_TODAS,):
            filtro &= Q(unidade__in=unidades)
        if not recortes or recortes == (RECORTE_TOTAL,):
            filtro &= Q(recorte__isnull=True)
        elif recortes != (RECORTE_TODOS,):
            filtro &= Q(recorte_id__in=[int(i) for i in recortes])
        if situacoes:
            filtro &= Q(situacao__in=situacoes)

        consulta = RegistroAnual.objects.filter(filtro)
        total = consulta.count()
        anotada = _registros_para_serializar(anotar_registros(consulta)).order_by(*ordenacao(ordem))
        itens, envelope = paginar(request, anotada, total, paginacao)
        envelope["results"] = s.RegistroSerializer(itens, many=True).data
        return Response(envelope)


def _registros_para_serializar(consulta):
    """Relações do registro serializado numa consulta só, mais os itens dos recortes."""
    return consulta.select_related(
        "estado", "regiao", "indicador", "indicador__fonte_taxa", "recorte", "fonte"
    ).prefetch_related(
        Prefetch("recorte__itens", queryset=RecorteItem.objects.order_by("dimensao"))
    )


class DetalheRegistro(RecursoV1):
    @extend_schema(
        operation_id="api_v1_registros_detalhe",
        summary="Um registro",
        description="O mesmo objeto de um item de /registros/; id inexistente → 404.",
        parameters=[FORMATO_JSON],
        responses=s.RegistroSerializer,
    )
    def get(self, request, version, id):
        self.parametros.validar()
        consulta = anotar_registros(RegistroAnual.objects.filter(pk=id))
        registro = _registros_para_serializar(consulta).first()
        if registro is None:
            raise Http404(f"Registro não encontrado: {id}.")
        return Response(s.RegistroSerializer(registro).data)


class ListaPopulacao(RecursoV1):
    parametros_permitidos = ("nivel", "uf", "regiao", "ano", "ano_min", "ano_max", "ordenar")
    paginado = True

    @extend_schema(
        operation_id="api_v1_populacao_lista",
        summary="População",
        description="Estimativas do IBGE usadas no cálculo das taxas (contrato, 4.6). Mesma regra "
        "de nível de /registros/: sem `nivel`, só as UFs.",
        parameters=[
            *PARAMETROS_DE_LOCALIDADE,
            *PARAMETROS_DE_ANOS,
            OpenApiParameter(
                "ordenar",
                str,
                description="Lista de `ano`, `localidade`, `valor`; `-` inverte. Ordem padrão: "
                "localidade (canônica), ano; depois `id`.",
            ),
            *PARAMETROS_DE_PAGINA,
            FORMATO_JSON,
        ],
        responses=s.PaginaDePopulacaoSerializer,
    )
    def get(self, request, version):
        p = self.parametros
        ufs, regioes = _siglas()
        locais = p.localidades(ufs, regioes)
        anos = p.anos(_intervalo_de_anos())
        ordem = p.ordenacao(set(CAMPOS_DE_ORDENACAO_DA_POPULACAO))
        paginacao = p.paginacao()
        p.validar()

        consulta = Populacao.objects.filter(_filtro_de_localidade(locais) & _filtro_de_anos(anos))
        total = consulta.count()
        ordenada = consulta.select_related("estado", "regiao", "fonte").order_by(
            *ordenacao(ordem, CAMPOS_DE_ORDENACAO_DA_POPULACAO, ORDEM_PADRAO_DA_POPULACAO)
        )
        itens, envelope = paginar(request, ordenada, total, paginacao)
        envelope["results"] = s.PopulacaoSerializer(itens, many=True).data
        return Response(envelope)


# Ranking e comparação (contrato, seções 4.8 e 4.9)


class _ConsultaDeUmIndicador(RecursoV1):
    """Regras comuns a /ranking/ e /comparacao/: um indicador, uma unidade, um recorte."""

    def _ler_indicador_unidade_recorte(self):
        """Indicador (objeto), unidade, recorte (objeto ou None) e os anos com registros deles.

        Acumula os erros no LeitorParametros; devolve None no lugar do que for inválido.
        """
        p = self.parametros
        indicadores = {
            i.slug: i for i in Indicador.objects.select_related("fonte_taxa", "indicador_pai")
        }
        slug = p.unico("indicador", set(indicadores), obrigatorio=True)
        unidade_pedida = p.unico("unidade", set(Unidade.values))
        ids_de_recorte = {str(i) for i in Recorte.objects.values_list("id", flat=True)}
        recorte_pedido = p.unico("recorte", {RECORTE_TOTAL, *ids_de_recorte})

        indicador = indicadores.get(slug) if slug else None
        if indicador is None:
            return None, None, None, set()
        combinacoes = set(
            RegistroAnual.objects.filter(indicador=indicador)
            .values_list("unidade", "recorte_id", "ano")
            .distinct()
        )
        if not combinacoes:
            p.erro(
                "indicador",
                f"O indicador {slug} não tem registros próprios; consulte os subtipos.",
            )
            return None, None, None, set()

        unidade = unidade_pedida or indicador.unidade_padrao
        if p.valido("unidade") and not any(u == unidade for u, _, _ in combinacoes):
            p.erro("unidade", f"O indicador {slug} não tem registros em {unidade}.")
            return indicador, None, None, set()

        recorte = None
        if recorte_pedido and recorte_pedido != RECORTE_TOTAL:
            recorte = Recorte.objects.prefetch_related(
                Prefetch("itens", queryset=RecorteItem.objects.order_by("dimensao"))
            ).get(id=int(recorte_pedido))
        recorte_id = recorte.id if recorte else None
        anos = {a for u, r, a in combinacoes if u == unidade and r == recorte_id}
        if p.valido("recorte") and recorte is not None and not anos:
            p.erro(
                "recorte",
                f"O recorte {recorte.id} não tem registros de {slug} em {unidade}.",
            )
        return indicador, unidade, recorte, anos

    @staticmethod
    def _recorte(recorte):
        return s.RecorteDoRegistroSerializer(recorte).data if recorte else None

    @staticmethod
    def _indicador(indicador):
        return s.IndicadorComBaseSerializer(indicador).data


PARAMETROS_DE_UM_INDICADOR = [
    OpenApiParameter("indicador", str, required=True, description="Um slug. Agrupador → 400."),
    OpenApiParameter(
        "unidade",
        str,
        enum=Unidade.values,
        description="Uma unidade; padrão: a unidade padrão do indicador.",
    ),
    OpenApiParameter(
        "recorte",
        str,
        description="`total` (padrão) ou um id de /recortes/. `todos` ou lista → 400.",
    ),
]


class Ranking(_ConsultaDeUmIndicador):
    parametros_permitidos = ("indicador", "ano", "criterio", "unidade", "recorte")

    @extend_schema(
        summary="Ranking das UFs",
        description="As 27 UFs em ordem decrescente do critério, sobre o valor já arredondado. "
        "Empates têm a mesma posição (1, 2, 2, 4) e se desempatam por sigla; UF sem dado vem ao "
        "final com `posicao: null`. Os parâmetros efetivos, inclusive os padrões resolvidos, vêm "
        "ecoados na resposta (contrato, 4.8).",
        parameters=[
            *PARAMETROS_DE_UM_INDICADOR,
            OpenApiParameter(
                "ano",
                int,
                description="Um ano; padrão: o último ano com registros do indicador.",
            ),
            OpenApiParameter(
                "criterio",
                str,
                enum=list(CRITERIOS_DO_RANKING),
                description="`taxa` (padrão), `valor` ou `participacao`.",
            ),
            FORMATO_JSON,
        ],
        responses=s.RankingSerializer,
    )
    def get(self, request, version):
        p = self.parametros
        indicador, unidade, recorte, anos = self._ler_indicador_unidade_recorte()
        ano = p.ano("ano", _intervalo_de_anos())
        criterio = p.unico("criterio", set(CRITERIOS_DO_RANKING)) or "taxa"

        if indicador is not None and unidade is not None and p.valido("ano"):
            if ano is None and anos:
                ano = max(anos)
            elif ano is not None and ano not in anos:
                p.erro("ano", f"O indicador {indicador.slug} não tem registros em {ano}.")
        if indicador is not None and p.valido("criterio"):
            if criterio == "taxa" and indicador.base_taxa is None:
                p.erro("criterio", f"O indicador {indicador.slug} não tem base de taxa.")
            sem_pai = (
                indicador.indicador_pai_id is None
                or not RegistroAnual.objects.filter(
                    indicador_id=indicador.indicador_pai_id
                ).exists()
            )
            if criterio == "participacao" and recorte is None and sem_pai:
                p.erro(
                    "criterio",
                    f"O indicador {indicador.slug} não tem referência de participação "
                    "(indicador-raiz ou filho de agrupador).",
                )
        p.validar()

        itens = []
        for posicao, registro in ranking(
            indicador.id, ano, unidade, recorte.id if recorte else None, criterio
        ):
            registro.posicao = posicao
            itens.append(registro)
        dados = {
            "indicador": self._indicador(indicador),
            "ano": ano,
            "criterio": criterio,
            "unidade": unidade,
            "recorte": self._recorte(recorte),
            "results": s.ItemDoRankingSerializer(itens, many=True).data,
        }
        return Response(dados)


class Comparacao(_ConsultaDeUmIndicador):
    parametros_permitidos = ("uf", "indicador", "ano_min", "ano_max", "unidade", "recorte")

    @extend_schema(
        summary="UF × região × Brasil",
        description="Três séries, nesta ordem: a UF, a região da UF e o Brasil, cada uma com os "
        "pontos por ano crescente (RF13; contrato, 4.9). Totais regionais calculados pelo projeto "
        "vêm com `metodo = soma_ufs`.",
        parameters=[
            OpenApiParameter("uf", str, required=True, description="Uma sigla de UF."),
            *PARAMETROS_DE_UM_INDICADOR,
            OpenApiParameter(
                "ano_min", int, description="Padrão: o primeiro ano com registros do indicador."
            ),
            OpenApiParameter(
                "ano_max", int, description="Padrão: o último ano com registros do indicador."
            ),
            FORMATO_JSON,
        ],
        responses=s.ComparacaoSerializer,
    )
    def get(self, request, version):
        p = self.parametros
        ufs, _ = _siglas()
        uf = p.unico("uf", ufs, maiusculas=True, obrigatorio=True)
        indicador, unidade, recorte, anos = self._ler_indicador_unidade_recorte()
        intervalo = _intervalo_de_anos()
        ano_min, ano_max = p.ano("ano_min", intervalo), p.ano("ano_max", intervalo)
        if ano_min is not None and ano_max is not None and ano_min > ano_max:
            p.erro("", "ano_min não pode ser maior que ano_max.")

        if indicador is not None and unidade is not None and anos:
            ano_min = min(anos) if ano_min is None else ano_min
            ano_max = max(anos) if ano_max is None else ano_max
            intervalo_valido = p.valido("ano_min") and p.valido("ano_max") and ano_min <= ano_max
            if intervalo_valido and not any(ano_min <= ano <= ano_max for ano in anos):
                p.erro(
                    "",
                    f"O indicador {indicador.slug} não tem registros entre {ano_min} e {ano_max}.",
                )
        p.validar()

        estado = Estado.objects.select_related("regiao").get(sigla=uf)
        series = [
            {"localidade": campos.localidade_de(localidade), "pontos": registros}
            for localidade, registros in comparacao(
                estado, indicador.id, unidade, recorte.id if recorte else None, ano_min, ano_max
            )
        ]
        dados = {
            "indicador": self._indicador(indicador),
            "unidade": unidade,
            "recorte": self._recorte(recorte),
            "ano_min": ano_min,
            "ano_max": ano_max,
            "series": s.SerieSerializer(series, many=True).data,
        }
        return Response(dados)


# Metadados (contrato, seção 4.10)


def _codigos_e_nomes(escolhas) -> list[dict]:
    return [{"codigo": valor, "nome": nome} for valor, nome in escolhas.choices]


class Metadados(RecursoV1):
    @extend_schema(
        summary="Metadados",
        description="Tudo o que o dashboard precisa para montar filtros e legendas numa "
        "requisição (RF09; contrato, 4.10): a carga atual, os anos, os níveis, as unidades, as "
        "situações do dado, os métodos, as fontes e a árvore de indicadores, com unidades, anos e "
        "recortes de cada um.",
        parameters=[FORMATO_JSON],
        responses=s.MetadadosSerializer,
    )
    def get(self, request, version):
        self.parametros.validar()
        indicadores = list(_indicadores())
        filhos: dict[int, list[Indicador]] = defaultdict(list)
        for indicador in indicadores:
            if indicador.indicador_pai_id is not None:
                filhos[indicador.indicador_pai_id].append(indicador)
        contexto = _contexto_dos_indicadores() | {"filhos": filhos}
        raizes = [i for i in indicadores if i.indicador_pai_id is None]
        minimo, maximo = _intervalo_de_anos()

        dados = {
            "carga": s.CargaSerializer(self.carga).data,
            "anos": {"min": minimo, "max": maximo},
            "niveis": list(NIVEIS),
            "unidades": _codigos_e_nomes(Unidade),
            "situacoes": _codigos_e_nomes(Situacao),
            "metodos": _codigos_e_nomes(Metodo),
            "fontes": s.FonteDoMetadadoSerializer(Fonte.objects.order_by("id"), many=True).data,
            "indicadores": s.NoDeIndicadorSerializer(raizes, many=True, context=contexto).data,
        }
        return Response(dados)
