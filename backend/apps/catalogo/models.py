"""Modelos de catálogo: FONTES, INDICADORES, RECORTES e RECORTE_ITENS.

- Fonte: origem dos dados (secretarias estaduais, IBGE, Senatran, Banco Central), com slug e ids
  estáveis (ADR 0005).
- Indicador: indicadores e subtipos de crime, em hierarquia pela autorrelação indicador_pai
  ("contido em", nunca "soma de"), com slug (usado na API), ordem, unidade_padrao, base_taxa e
  fonte_taxa (fonte do denominador da taxa).
- Recorte e RecorteItem: grupos de agentes, formados por pares de dimensão e valor, como
  corporacao = Polícia Militar.

O conteúdo vem de catalogo/referencia.py e só é gravado pelo comando importar_anuario (RNF06).
"""

from django.db import models
from django.db.models import Q

from apps.registros.escolhas import Unidade


class Fonte(models.Model):
    slug = models.SlugField(max_length=50, unique=True)
    nome = models.CharField(max_length=200)
    descricao = models.TextField()
    url = models.URLField(max_length=500)

    class Meta:
        ordering = ["id"]
        verbose_name_plural = "fontes"

    def __str__(self) -> str:
        return self.nome


class BaseTaxa(models.TextChoices):
    """Denominador das taxas publicadas pelo FBSP."""

    HABITANTES = "100 mil habitantes"
    MULHERES = "100 mil mulheres"
    VEICULOS = "100 mil veículos"
    INSTITUICOES = "100 instituições"


class Indicador(models.Model):
    slug = models.SlugField(max_length=60, unique=True)
    nome = models.CharField(max_length=120)
    descricao = models.TextField(blank=True)
    unidade_padrao = models.CharField(max_length=11, choices=Unidade)
    base_taxa = models.CharField(  # noqa: DJ001 nulo = sem base; par de fonte_taxa no CHECK
        max_length=20, choices=BaseTaxa, null=True, blank=True
    )
    fonte_taxa = models.ForeignKey(
        Fonte, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    indicador_pai = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True, related_name="subtipos"
    )
    ordem = models.PositiveSmallIntegerField(unique=True)

    class Meta:
        ordering = ["ordem"]
        verbose_name_plural = "indicadores"
        constraints = [
            # A fonte do denominador existe se e somente se o indicador tem base de taxa (ADR 0005).
            models.CheckConstraint(
                condition=Q(base_taxa__isnull=True, fonte_taxa__isnull=True)
                | Q(base_taxa__isnull=False, fonte_taxa__isnull=False),
                name="indicador_base_taxa_com_fonte",
            ),
        ]

    def __str__(self) -> str:
        return self.slug


class Dimensao(models.TextChoices):
    """Únicas dimensões de recorte do escopo (ADR 0004)."""

    CORPORACAO = "corporacao", "Corporação"
    SITUACAO_POLICIAL = "situacao_policial", "Situação do policial"


class Recorte(models.Model):
    chave = models.CharField(max_length=200, unique=True)  # "dimensao=valor;..." em ordem
    rotulo = models.CharField(max_length=200)

    class Meta:
        ordering = ["chave"]

    def __str__(self) -> str:
        return self.rotulo


class RecorteItem(models.Model):
    recorte = models.ForeignKey(Recorte, on_delete=models.CASCADE, related_name="itens")
    dimensao = models.CharField(max_length=20, choices=Dimensao)
    valor = models.CharField(max_length=100)

    class Meta:
        ordering = ["recorte", "dimensao"]
        constraints = [
            models.UniqueConstraint(fields=["recorte", "dimensao"], name="recorte_item_unico"),
        ]

    def __str__(self) -> str:
        return f"{self.dimensao}={self.valor}"
