"""Comando administrativo de carga dos dados: python manage.py importar_anuario.

É a única forma de gravar dados no banco (RNF06). A importação é idempotente (RF12): executada de
novo, atualiza os registros existentes em vez de duplicá-los. O fluxo está em
apps/importacao/processo.py e segue docs/importacao.md, seção 4.1.
"""

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.importacao.erros import ErroImportacao
from apps.importacao.processo import importar
from apps.importacao.validacao import Severidade


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
        parser.add_argument(
            "--manifesto",
            type=Path,
            default=None,
            help="Arquivo com o SHA-256 de cada planilha (padrão: README.md acima de --dados).",
        )
        parser.add_argument(
            "--somente-validar",
            action="store_true",
            help="Lê, confere e gera o relatório sem gravar nada no banco.",
        )
        parser.add_argument(
            "--estrito",
            action="store_true",
            help="Termina com erro se o relatório tiver alguma divergência.",
        )

    def handle(self, *args, **opcoes):
        dados: Path = opcoes["dados"]
        if not dados.is_dir():
            raise CommandError(f"Diretório de dados não encontrado: {dados}")
        manifesto = opcoes["manifesto"] or dados.parent / "README.md"

        planilhas = sorted(p.name for p in dados.iterdir() if p.suffix in {".xlsx", ".ods"})
        self.stdout.write(f"Planilhas encontradas: {', '.join(planilhas) or 'nenhuma'}")

        try:
            resultado = importar(
                dados,
                opcoes["relatorio"],
                manifesto,
                somente_validar=opcoes["somente_validar"],
            )
        except ErroImportacao as erro:
            raise CommandError(f"Importação desfeita: {erro}") from erro

        relatorio = resultado.relatorio
        acao = "validada (nada gravado)" if opcoes["somente_validar"] else "concluída"
        self.stdout.write(
            f"Carga {resultado.versao} {acao}: {resultado.registros} registros "
            f"({resultado.calculados} regionais calculados) e {resultado.populacao} populações."
        )
        for severidade in Severidade:
            self.stdout.write(f"  {severidade}: {len(relatorio.de(severidade))}")
        csv, md = resultado.arquivos_relatorio
        self.stdout.write(f"Relatório: {csv} e {md}")

        if relatorio.tem_divergencias:
            mensagem = f"{len(relatorio.de(Severidade.DIVERGENCIA))} divergência(s) no relatório."
            if opcoes["estrito"]:
                raise CommandError(mensagem)
            self.stdout.write(self.style.WARNING(mensagem))
        else:
            self.stdout.write(self.style.SUCCESS("Nenhuma divergência acima da tolerância."))
