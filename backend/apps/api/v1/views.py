"""Views da versão 1. Todas são somente leitura (APIView com GET; RNF06, regra 15).

`RecursoV1` aplica, em toda view, a ordem de verificação do contrato: método (405), formato (406),
carga concluída (503, seção 7.1) e só então os parâmetros (400, seção 2), lidos por
`LeitorParametros` e validados de uma vez. Toda resposta 200 leva `Vary: Accept` (regra 27).
"""

from collections import defaultdict
from dataclasses import dataclass, field

from django.db.models import Prefetch
from django.http import Http404
from django.utils.cache import patch_vary_headers
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import exceptions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.erros import SemCargaConcluida
from apps.api.v1 import serializers as s
from apps.api.v1.parametros import LeitorParametros
from apps.catalogo.models import Fonte, Indicador, Recorte, RecorteItem
from apps.importacao.models import Carga
from apps.localidades.models import Estado, Regiao
from apps.registros.models import RegistroAnual

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
