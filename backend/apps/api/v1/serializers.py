"""Serializers da versão 1 (contrato, seção 4).

Valores e taxas são serializados como texto pelos campos de apps/api/v1/campos.py, o que preserva
a precisão do tipo NUMERIC (RNF10). Os catálogos não levam fonte por item (CLAUDE.md, regra 21).
"""

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.catalogo.models import Fonte, Indicador, Recorte
from apps.localidades.models import Estado, Regiao
from apps.registros.escolhas import Unidade


class FonteResumoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Fonte
        fields = ["id", "nome"]


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
    fonte_taxa = FonteResumoSerializer(allow_null=True)
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
