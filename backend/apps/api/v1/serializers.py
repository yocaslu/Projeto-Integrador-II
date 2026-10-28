"""Serializers da versão 1 (contrato, seção 4).

Valores e taxas são serializados como texto pelos campos de apps/api/v1/campos.py, o que preserva
a precisão do tipo NUMERIC (RNF10). Os catálogos não levam fonte por item (CLAUDE.md, regra 21).
"""

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.api.v1 import campos
from apps.catalogo.models import Fonte, Indicador, Recorte
from apps.localidades.models import Estado, Regiao
from apps.registros.escolhas import Metodo, Situacao, Unidade


class FonteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Fonte
        fields = ["id", "slug", "nome", "descricao", "url"]


class RegiaoResumoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Regiao
        fields = ["sigla", "nome"]


class RegiaoSerializer(serializers.ModelSerializer):
    estados = serializers.SerializerMethodField(help_text="Siglas das UFs; no Brasil, as 27.")

    class Meta:
        model = Regiao
        fields = ["sigla", "nome", "tipo", "codigo_ibge", "estados"]

    def get_estados(self, regiao: Regiao) -> list[str]:
        if regiao.tipo == Regiao.Tipo.PAIS:
            return self.context["todas_as_ufs"]
        return [estado.sigla for estado in regiao.estados.all()]


class EstadoSerializer(serializers.ModelSerializer):
    regiao = RegiaoResumoSerializer()

    class Meta:
        model = Estado
        fields = ["sigla", "nome", "codigo_ibge", "regiao"]


class RecorteResumoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recorte
        fields = ["id", "rotulo"]


class RecorteItemSerializer(serializers.Serializer):
    dimensao = serializers.CharField()
    valor = serializers.CharField()


class RecorteSerializer(serializers.ModelSerializer):
    itens = RecorteItemSerializer(many=True)
    indicadores = serializers.SerializerMethodField(
        help_text="Slugs dos indicadores com registros nesse recorte."
    )

    class Meta:
        model = Recorte
        fields = ["id", "rotulo", "chave", "itens", "indicadores"]

    def get_indicadores(self, recorte: Recorte) -> list[str]:
        return self.context["indicadores_do_recorte"].get(recorte.id, [])


class IndicadorSerializer(serializers.ModelSerializer):
    """Item de /indicadores/ (contrato, 4.3). Lista plana; a árvore fica em /metadados/."""

    unidades = serializers.SerializerMethodField(
        help_text="Unidades com registros, na ordem vitimas, ocorrencias."
    )
    fonte_taxa = campos.FonteResumoSerializer(allow_null=True)
    indicador_pai = serializers.SlugRelatedField(slug_field="slug", read_only=True)
    subtipos = serializers.SerializerMethodField(help_text="Slugs dos filhos diretos, na ordem.")
    possui_registros = serializers.SerializerMethodField()
    anos = serializers.SerializerMethodField(help_text="Anos com registros, crescentes.")
    recortes = serializers.SerializerMethodField()

    class Meta:
        model = Indicador
        fields = [
            "slug",
            "nome",
            "descricao",
            "unidade_padrao",
            "unidades",
            "base_taxa",
            "fonte_taxa",
            "indicador_pai",
            "subtipos",
            "possui_registros",
            "anos",
            "recortes",
        ]

    def _resumo(self, indicador: Indicador):
        return self.context["resumo"].get(indicador.id)

    def get_unidades(self, indicador: Indicador) -> list[str]:
        resumo = self._resumo(indicador)
        return [u for u in Unidade.values if resumo and u in resumo.unidades]

    def get_subtipos(self, indicador: Indicador) -> list[str]:
        return self.context["subtipos"].get(indicador.id, [])

    def get_possui_registros(self, indicador: Indicador) -> bool:
        return self._resumo(indicador) is not None

    def get_anos(self, indicador: Indicador) -> list[int]:
        resumo = self._resumo(indicador)
        return sorted(resumo.anos) if resumo else []

    @extend_schema_field(RecorteResumoSerializer(many=True))
    def get_recortes(self, indicador: Indicador) -> list[dict]:
        resumo = self._resumo(indicador)
        if not resumo:
            return []
        recortes = sorted(
            (self.context["recortes"][i] for i in resumo.recortes), key=lambda r: r.chave
        )
        return RecorteResumoSerializer(recortes, many=True).data


# Registros e população (contrato, seções 4.6 e 4.7.4)


class IndicadorResumoSerializer(serializers.Serializer):
    slug = serializers.CharField()
    nome = serializers.CharField()


class RecorteDoRegistroSerializer(serializers.Serializer):
    """`{"id", "rotulo", "itens"}`; `itens` na ordem da chave (dimensões em ordem alfabética)."""

    id = serializers.IntegerField()
    rotulo = serializers.CharField()
    itens = RecorteItemSerializer(many=True)


class RegistroSerializer(serializers.Serializer):
    """Item de /registros/ e corpo de /registros/{id}/ (contrato, 4.7.4)."""

    id = serializers.IntegerField()
    ano = serializers.IntegerField()
    localidade = campos.LocalidadeSerializer(source="*")
    indicador = IndicadorResumoSerializer()
    recorte = RecorteDoRegistroSerializer(allow_null=True)
    unidade = serializers.ChoiceField(choices=Unidade.choices)
    valor = campos.CampoInteiro(allow_null=True)
    situacao = serializers.ChoiceField(choices=Situacao.choices)
    metodo = serializers.ChoiceField(choices=Metodo.choices)
    taxa = campos.TaxaSerializer(source="*")
    taxa_publicada = campos.CampoPrecisaoGuardada(allow_null=True)
    variacao = campos.VariacaoSerializer(source="*")
    participacao = campos.ParticipacaoSerializer(source="*")
    fonte = campos.FonteResumoSerializer()
    observacao = serializers.CharField(allow_null=True)


class PopulacaoSerializer(serializers.Serializer):
    """Item de /populacao/ (contrato, 4.6)."""

    id = serializers.IntegerField()
    ano = serializers.IntegerField()
    localidade = campos.LocalidadeSerializer(source="*")
    valor = campos.CampoInteiro()
    fonte = campos.FonteResumoSerializer()


class _Pagina(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)


class PaginaDeRegistrosSerializer(_Pagina):
    results = RegistroSerializer(many=True)


class PaginaDePopulacaoSerializer(_Pagina):
    results = PopulacaoSerializer(many=True)


# Ranking e comparação (contrato, seções 4.8 e 4.9)


class IndicadorComBaseSerializer(serializers.Serializer):
    slug = serializers.CharField()
    nome = serializers.CharField()
    base_taxa = serializers.CharField(allow_null=True)


class LocalidadeFixaSerializer(serializers.Serializer):
    """A localidade de uma série, montada por `campos.localidade_de`."""

    nivel = serializers.CharField()
    codigo = serializers.CharField()
    codigo_ibge = serializers.CharField()
    nome = serializers.CharField()


class _ValoresDoRegistro(serializers.Serializer):
    """Campos de valor de um registro, sem `taxa_publicada`, que fica em /registros/."""

    valor = campos.CampoInteiro(allow_null=True)
    situacao = serializers.ChoiceField(choices=Situacao.choices)
    metodo = serializers.ChoiceField(choices=Metodo.choices)
    taxa = campos.TaxaSerializer(source="*")
    variacao = campos.VariacaoSerializer(source="*")
    participacao = campos.ParticipacaoSerializer(source="*")
    fonte = campos.FonteResumoSerializer()
    observacao = serializers.CharField(allow_null=True)


class ItemDoRankingSerializer(_ValoresDoRegistro):
    posicao = serializers.IntegerField(allow_null=True)
    localidade = campos.LocalidadeSerializer(source="*")

    class Meta:
        fields = ["posicao", "localidade", *_ValoresDoRegistro._declared_fields]

    def get_fields(self):
        campos_ = super().get_fields()
        return {nome: campos_[nome] for nome in self.Meta.fields}


class RankingSerializer(serializers.Serializer):
    indicador = IndicadorComBaseSerializer()
    ano = serializers.IntegerField()
    criterio = serializers.ChoiceField(choices=["taxa", "valor", "participacao"])
    unidade = serializers.ChoiceField(choices=Unidade.choices)
    recorte = RecorteDoRegistroSerializer(allow_null=True)
    results = ItemDoRankingSerializer(many=True)


class PontoSerializer(_ValoresDoRegistro):
    ano = serializers.IntegerField()

    class Meta:
        fields = ["ano", *_ValoresDoRegistro._declared_fields]

    def get_fields(self):
        campos_ = super().get_fields()
        return {nome: campos_[nome] for nome in self.Meta.fields}


class SerieSerializer(serializers.Serializer):
    localidade = LocalidadeFixaSerializer()
    pontos = PontoSerializer(many=True)


class ComparacaoSerializer(serializers.Serializer):
    indicador = IndicadorComBaseSerializer()
    unidade = serializers.ChoiceField(choices=Unidade.choices)
    recorte = RecorteDoRegistroSerializer(allow_null=True)
    ano_min = serializers.IntegerField()
    ano_max = serializers.IntegerField()
    series = SerieSerializer(many=True)


# Metadados (contrato, seção 4.10)


class CodigoNomeSerializer(serializers.Serializer):
    codigo = serializers.CharField()
    nome = serializers.CharField()


class CargaSerializer(serializers.Serializer):
    versao = serializers.CharField()
    concluida_em = serializers.DateTimeField()
    total_registros = serializers.IntegerField()
    arquivos = serializers.ListField(child=serializers.DictField(child=serializers.CharField()))


class IntervaloDeAnosSerializer(serializers.Serializer):
    min = serializers.IntegerField()
    max = serializers.IntegerField()


class FonteDoMetadadoSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    slug = serializers.CharField()
    nome = serializers.CharField()


class NoDeIndicadorSerializer(IndicadorSerializer):
    """Nó da árvore de indicadores: os campos de um item de /indicadores/, na mesma ordem, com
    `subtipos` trazendo os objetos dos filhos em vez dos slugs (contrato, 4.10)."""

    subtipos = serializers.SerializerMethodField()

    def get_subtipos(self, indicador: Indicador) -> list[dict]:
        filhos = self.context["filhos"].get(indicador.id, [])
        return NoDeIndicadorSerializer(filhos, many=True, context=self.context).data


# A árvore é recursiva: no OpenAPI, `subtipos` referencia o próprio componente NoDeIndicador.
extend_schema_field(NoDeIndicadorSerializer(many=True))(NoDeIndicadorSerializer.get_subtipos)


class MetadadosSerializer(serializers.Serializer):
    carga = CargaSerializer()
    anos = IntervaloDeAnosSerializer()
    niveis = serializers.ListField(child=serializers.CharField())
    unidades = CodigoNomeSerializer(many=True)
    situacoes = CodigoNomeSerializer(many=True)
    metodos = CodigoNomeSerializer(many=True)
    fontes = FonteDoMetadadoSerializer(many=True)
    indicadores = NoDeIndicadorSerializer(many=True)
