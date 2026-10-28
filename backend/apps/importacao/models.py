"""Modelo CARGAS: cada execução do comando importar_anuario.

A carga atual (a concluída com o maior concluida_em) dá a versão usada no ETag e em /metadados/
(contrato, seções 4.10 e 7). Sem nenhuma carga concluída, a API responde 503 (ADR 0005).
"""

from django.db import models


class CargaQuerySet(models.QuerySet):
    def atual(self) -> Carga | None:
        """Carga concluída mais recente; cargas em andamento ou com falha não contam."""
        return self.filter(status=Carga.Status.CONCLUIDA).order_by("-concluida_em", "-id").first()


class Carga(models.Model):
    class Status(models.TextChoices):
        EM_ANDAMENTO = "em_andamento", "Em andamento"
        CONCLUIDA = "concluida", "Concluída"
        FALHOU = "falhou", "Falhou"

    versao = models.CharField(max_length=12)  # sha256 dos hashes dos arquivos, 12 primeiros
    arquivos = models.JSONField(default=list)  # [{"nome": ..., "sha256": ...}]
    iniciada_em = models.DateTimeField(auto_now_add=True)
    concluida_em = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=12, choices=Status, default=Status.EM_ANDAMENTO)
    total_registros = models.PositiveIntegerField(null=True, blank=True)

    objects = CargaQuerySet.as_manager()

    class Meta:
        ordering = ["-iniciada_em"]

    def __str__(self) -> str:
        return f"{self.versao} ({self.status})"
