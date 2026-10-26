from django.apps import AppConfig


class ImportacaoConfig(AppConfig):
    """Importação das planilhas do FBSP e do IBGE (RF01, RF12).

    É a única parte do sistema que grava no banco (RNF06).
    """

    name = "apps.importacao"
    verbose_name = "Importação"
