"""Modelo REGISTROS_ANUAIS, a tabela de fatos.

Cada registro guarda o valor de um indicador em um ano e em uma unidade (vitimas ou
ocorrencias, ADR 0004), para um estado ou uma região e, opcionalmente, para um recorte.
Restrições no banco (regra 14):

- exatamente um entre estado e regiao preenchido (CheckConstraint);
- unicidade de localidade, indicador, recorte, unidade e ano com nulls_distinct=False
  (NULLS NOT DISTINCT, PostgreSQL 18);
- valor e taxa_publicada em DecimalField, que corresponde a NUMERIC (RNF10);
- situacao com as marcações originais: informado, inexistente ou nao_disponivel (RF11), coerente
  com o valor ("-" → 0; "..." → nulo);
- metodo: publicado (lido da planilha) ou soma_ufs (total regional calculado na importação
  como soma das UFs, nos indicadores cuja tabela não publica regiões; ver ADR 0002). Em
  soma_ufs, taxa_publicada é nula, origem lista as células somadas e observacao traz as notas
  das UFs (docs/importacao.md, seção 4.8).
"""

from django.db import models
from django.db.models import F, Q, Value
from django.db.models.functions import Coalesce

from apps.localidades.models import LOCALIDADE_EXCLUSIVA
from apps.registros.escolhas import Metodo, Situacao, Unidade


class RegistroAnual(models.Model):
    estado = models.ForeignKey(
        "localidades.Estado",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="registros",
    )
    regiao = models.ForeignKey(
        "localidades.Regiao",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="registros",
    )
    indicador = models.ForeignKey(
        "catalogo.Indicador", on_delete=models.PROTECT, related_name="registros"
    )
    recorte = models.ForeignKey(
        "catalogo.Recorte",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="registros",
    )
    fonte = models.ForeignKey("catalogo.Fonte", on_delete=models.PROTECT, related_name="+")
    ano = models.PositiveSmallIntegerField()
    unidade = models.CharField(max_length=11, choices=Unidade)
    valor = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    taxa_publicada = models.DecimalField(max_digits=24, decimal_places=12, null=True, blank=True)
    situacao = models.CharField(max_length=14, choices=Situacao)
    metodo = models.CharField(max_length=9, choices=Metodo, default=Metodo.PUBLICADO)
    origem = models.CharField(max_length=200)  # célula da planilha, ex.: "T08!D15"
    # Notas metodológicas do FBSP; nulo quando não há nota, como a API expõe (contrato, 4.7.4).
    observacao = models.TextField(null=True, blank=True)  # noqa: DJ001 nulo = sem nota

    class Meta:
        verbose_name = "registro anual"
        verbose_name_plural = "registros anuais"
        constraints = [
            models.CheckConstraint(condition=LOCALIDADE_EXCLUSIVA, name="registro_localidade"),
            models.UniqueConstraint(
                fields=["estado", "regiao", "indicador", "recorte", "unidade", "ano"],
                name="registro_unico",
                nulls_distinct=False,
            ),
            models.CheckConstraint(
                condition=Q(situacao=Situacao.INFORMADO, valor__isnull=False)
                | Q(situacao=Situacao.INEXISTENTE, valor=0)
                | Q(situacao=Situacao.NAO_DISPONIVEL, valor__isnull=True),
                name="registro_valor_coerente_com_situacao",
            ),
            models.CheckConstraint(
                condition=~Q(metodo=Metodo.SOMA_UFS) | Q(taxa_publicada__isnull=True),
                name="registro_soma_ufs_sem_taxa_publicada",
            ),
        ]
        indexes = [
            models.Index(fields=["indicador", "unidade", "ano"], name="registro_indicador_ano"),
            # Mesmas expressões das subconsultas de apps/registros/queries.py (ano anterior,
            # total do indicador e do pai), que comparam campos anuláveis com COALESCE.
            models.Index(
                Coalesce("estado", Value(0)),
                Coalesce("regiao", Value(0)),
                F("indicador"),
                Coalesce("recorte", Value(0)),
                F("unidade"),
                F("ano"),
                name="registro_chave_subconsultas",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.estado or self.regiao} {self.indicador_id} {self.unidade} {self.ano}"
