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
from apps.api.v1 import serializers as s
from apps.api.v1.parametros import Anos, LeitorParametros, Localidades
from apps.catalogo.models import Fonte, Indicador, Recorte, RecorteItem
from apps.importacao.models import Carga
from apps.localidades.models import Estado, Populacao, Regiao
from apps.registros.escolhas import Situacao, Unidade
from apps.registros.models import RegistroAnual
from apps.registros.queries import (
    CAMPOS_DE_ORDENACAO,
    CAMPOS_DE_ORDENACAO_DA_POPULACAO,
    ORDEM_PADRAO_DA_POPULACAO,
    anotar_registros,
    ordenacao,
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
