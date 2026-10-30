"""Carga real para o teste de desempenho (ADR 0005, seção 4).

A planilha completa de dados/brutos/ é importada uma vez por sessão, pelo próprio comando
importar_anuario (1.980 registros e 462 populações), fora das transações dos testes, e apagada no
fim, para não sobrar nada no banco de teste.
"""

from io import StringIO
from pathlib import Path

import pytest
from django.conf import settings
from django.core.management import call_command

from apps.catalogo.models import Fonte, Indicador, Recorte, RecorteItem
from apps.importacao.models import Carga
from apps.localidades.models import Estado, Populacao, Regiao
from apps.registros.models import RegistroAnual

DADOS = Path(settings.BASE_DIR).parent / "dados"


@pytest.fixture(scope="session")
def carga_real(django_db_setup, django_db_blocker, tmp_path_factory):
    with django_db_blocker.unblock():
        call_command(
            "importar_anuario",
            dados=DADOS / "brutos",
            relatorio=tmp_path_factory.mktemp("relatorios"),
            stdout=StringIO(),
        )
        assert RegistroAnual.objects.count() == 1980
        yield
        Indicador.objects.update(indicador_pai=None)  # PROTECT na própria tabela
        for modelo in (
            RegistroAnual,
            Populacao,
            RecorteItem,
            Recorte,
            Estado,
            Regiao,
            Indicador,
            Fonte,
            Carga,
        ):
            modelo.objects.all().delete()
