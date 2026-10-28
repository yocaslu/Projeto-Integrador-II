"""Comando de apoio: python manage.py inspecionar_planilha.

A planilha muda de layout entre edições. Antes de ajustar apps/importacao/mapeamento.py, este
comando mostra, para cada tabela do mapeamento (ou para as abas pedidas), a linha da âncora, os
caminhos de cabeçalho de cada coluna e o bloco com que cada coluna casa. Só lê; não grava nada.
"""

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.catalogo import referencia
from apps.importacao.erros import ErroImportacao
from apps.importacao.leitores import fbsp
from apps.importacao.mapeamento import TABELAS


class Command(BaseCommand):
    help = "Mostra âncoras e caminhos de cabeçalho das tabelas da planilha do FBSP."

    def add_arguments(self, parser):
        parser.add_argument(
            "--planilha",
            type=Path,
            default=settings.DADOS_BRUTOS_DIR / "anuario-2026.xlsx",
            help="Planilha do FBSP (padrão: DADOS_BRUTOS_DIR/anuario-2026.xlsx).",
        )
        parser.add_argument(
            "abas", nargs="*", help="Abas a inspecionar (padrão: as do mapeamento)."
        )

    def handle(self, *args, **opcoes):
        caminho: Path = opcoes["planilha"]
        if not caminho.is_file():
            raise CommandError(f"Planilha não encontrada: {caminho}")
        wb = fbsp.abrir(caminho)
        tabelas = {t.aba: t for t in TABELAS}
        abas = opcoes["abas"] or list(tabelas)
        base_taxa = {
            i.slug: i.base_taxa.value if i.base_taxa else None for i in referencia.INDICADORES
        }

        self.stdout.write(f"{len(wb.sheetnames)} abas; tabelas: {', '.join(abas)}")
        for aba in abas:
            if aba not in wb.sheetnames:
                raise CommandError(f"Aba {aba} não encontrada.")
            tabela = tabelas.get(aba)
            grade = fbsp.Grade(wb[aba])
            self.stdout.write(f"\n== {aba}")
            if tabela is None:
                self.stdout.write("   (fora do mapeamento; mostrando as 12 primeiras linhas)")
                for linha in range(1, min(grade.max_row, 12) + 1):
                    valores = [grade.valor(linha, c) for c in range(1, grade.max_col + 1)]
                    self.stdout.write(f"   {linha}: {[v for v in valores if v is not None]}")
                continue
            try:
                ancora = fbsp.achar_ancora(grade, tabela.ancora, aba)
            except ErroImportacao as erro:
                self.stdout.write(self.style.ERROR(f"   {erro}"))
                continue
            self.stdout.write(f"   âncora na linha {ancora}: {grade.ws.cell(ancora, 1).value!r}")
            for coluna, caminho_col in fbsp.caminhos(
                grade, ancora, tabela.linhas_cabecalho
            ).items():
                letra = fbsp.coordenada(ancora, coluna).rstrip("0123456789")
                self.stdout.write(f"   {letra}: {caminho_col}")
            try:
                linha_fonte = fbsp.achar_fonte(grade, ancora + tabela.linhas_cabecalho, aba)
                notas = fbsp.ler_notas(grade, linha_fonte)
                fbsp.resolver_colunas(grade, ancora, tabela, notas, base_taxa)
            except ErroImportacao as erro:
                self.stdout.write(self.style.ERROR(f"   mapeamento: {erro}"))
            else:
                self.stdout.write(self.style.SUCCESS("   mapeamento: todas as colunas resolvidas"))
