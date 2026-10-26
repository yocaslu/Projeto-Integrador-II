"""Comando administrativo de carga dos dados: python manage.py importar_anuario.

É a única forma de gravar dados no banco (RNF06). A importação deve ser idempotente (RF12):
executada de novo, atualiza os registros existentes em vez de duplicá-los.
"""

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Importa a planilha do FBSP e as estimativas do IBGE e gera o relatório de validação."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dados",
            type=Path,
            default=settings.DADOS_BRUTOS_DIR,
            help="Diretório com as planilhas de origem (padrão: DADOS_BRUTOS_DIR).",
        )
        parser.add_argument(
            "--relatorio",
            type=Path,
            default=settings.DADOS_RELATORIOS_DIR,
            help="Diretório do relatório de validação (padrão: DADOS_RELATORIOS_DIR).",
        )

    def handle(self, *args, **opcoes):
        dados: Path = opcoes["dados"]
        if not dados.is_dir():
            raise CommandError(f"Diretório de dados não encontrado: {dados}")

        planilhas = sorted(p.name for p in dados.iterdir() if p.suffix in {".xlsx", ".ods"})
        self.stdout.write(f"Planilhas encontradas: {', '.join(planilhas) or 'nenhuma'}")

        # Etapas a implementar, dentro de uma transação:
        # 1. carregar regiões, estados e fontes;
        # 2. ler as estimativas do IBGE (leitores.ibge) e gravar POPULACAO;
        # 3. ler a planilha do FBSP (leitores.fbsp), normalizar as células e gravar
        #    INDICADORES, RECORTES e REGISTROS_ANUAIS com update_or_create;
        # 4. gravar a data e a versão da carga, usadas no ETag (RNF11);
        # 5. gerar o relatório de validação (validacao) em opcoes["relatorio"].
        self.stdout.write(self.style.WARNING("Importação ainda não implementada."))
