"""Modelos de localidade: REGIOES, ESTADOS e POPULACAO.

- Regiao: as cinco regiões e o total nacional, distinguidos pelo atributo tipo (regiao ou pais).
  A sigla (BR, N, NE, SE, S, CO) é única; o codigo_ibge repete entre tipos (Brasil e Norte são
  ambos 1), por isso a unicidade é por (tipo, codigo_ibge).
- Estado: as 27 UFs, cada uma ligada a exatamente uma região.
- Populacao: estimativas do IBGE de 2024 e 2025 para estados, regiões e Brasil, usadas no
  cálculo das taxas por 100 mil habitantes (RF05). Cada linha aponta para um estado ou para
  uma região, nunca para os dois.

O conteúdo vem de localidades/referencia.py e das planilhas do IBGE, e só é gravado pelo comando
importar_anuario (RNF06).
"""

from django.db import models
from django.db.models import Q


class Regiao(models.Model):
    class Tipo(models.TextChoices):
        REGIAO = "regiao", "Região"
        PAIS = "pais", "País"

    sigla = models.CharField(max_length=2, unique=True)
    nome = models.CharField(max_length=50)
    tipo = models.CharField(max_length=6, choices=Tipo)
    codigo_ibge = models.CharField(max_length=2)

    class Meta:
        # "pais" < "regiao": o Brasil vem primeiro, depois as regiões por código do IBGE.
        ordering = ["tipo", "codigo_ibge"]
        verbose_name = "região"
        verbose_name_plural = "regiões"
        constraints = [
            models.UniqueConstraint(
                fields=["tipo", "codigo_ibge"], name="regiao_codigo_ibge_unico"
            ),
        ]

    def __str__(self) -> str:
        return self.sigla


class Estado(models.Model):
    sigla = models.CharField(max_length=2, unique=True)
    nome = models.CharField(max_length=50)
    codigo_ibge = models.CharField(max_length=2, unique=True)
    regiao = models.ForeignKey(
        Regiao,
        on_delete=models.PROTECT,
        related_name="estados",
        limit_choices_to={"tipo": Regiao.Tipo.REGIAO},
    )

    class Meta:
        ordering = ["sigla"]

    def __str__(self) -> str:
        return self.sigla


LOCALIDADE_EXCLUSIVA = Q(estado__isnull=False, regiao__isnull=True) | Q(
    estado__isnull=True, regiao__isnull=False
)
"""Exatamente um entre estado e regiao preenchido (POPULACAO e REGISTROS_ANUAIS)."""


class Populacao(models.Model):
    estado = models.ForeignKey(
        Estado, on_delete=models.PROTECT, null=True, blank=True, related_name="populacoes"
    )
    regiao = models.ForeignKey(
        Regiao, on_delete=models.PROTECT, null=True, blank=True, related_name="populacoes"
    )
    fonte = models.ForeignKey("catalogo.Fonte", on_delete=models.PROTECT, related_name="+")
    ano = models.PositiveSmallIntegerField()
    valor = models.DecimalField(max_digits=12, decimal_places=0)

    class Meta:
        verbose_name = "população"
        verbose_name_plural = "populações"
        constraints = [
            models.CheckConstraint(condition=LOCALIDADE_EXCLUSIVA, name="populacao_localidade"),
            models.UniqueConstraint(
                fields=["estado", "regiao", "ano"],
                name="populacao_unica",
                nulls_distinct=False,
            ),
        ]

    def __str__(self) -> str:
        return f"{self.estado or self.regiao} {self.ano}"
