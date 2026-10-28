"""Valores fixos dos registros: situação do dado, método e unidade.

Ficam fora de models.py para que a importação (linhas, normalização e agregação) use as mesmas
definições sem depender do registro de apps do Django. Os rótulos são os que /metadados/ expõe
(contrato, seção 4.10).
"""

from django.db import models


class Situacao(models.TextChoices):
    """Marcação original da planilha (RF11)."""

    INFORMADO = "informado", "Informado"
    INEXISTENTE = "inexistente", "Fenômeno inexistente"  # "-" na planilha; valor 0
    NAO_DISPONIVEL = "nao_disponivel", "Informação não disponível"  # "..."; valor nulo


class Metodo(models.TextChoices):
    """Como o valor de um registro foi obtido (RF11, ADR 0002)."""

    PUBLICADO = "publicado", "Publicado pelo FBSP"  # lido de uma célula da planilha
    SOMA_UFS = "soma_ufs", "Calculado pelo projeto como soma das UFs"


class Unidade(models.TextChoices):
    """Unidade do valor do registro (ADR 0004). Um fato com duas vítimas conta 2 e 1."""

    VITIMAS = "vitimas", "Número de vítimas"
    OCORRENCIAS = "ocorrencias", "Número de ocorrências"
