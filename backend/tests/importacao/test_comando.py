from io import StringIO

import pytest
from django.core.management import CommandError, call_command


def test_comando_lista_as_planilhas(tmp_path):
    (tmp_path / "anuario.xlsx").touch()
    (tmp_path / "pop.ods").touch()
    saida = StringIO()

    call_command("importar_anuario", dados=tmp_path, relatorio=tmp_path, stdout=saida)

    assert "anuario.xlsx, pop.ods" in saida.getvalue()


def test_comando_falha_sem_diretorio(tmp_path):
    with pytest.raises(CommandError, match="não encontrado"):
        call_command("importar_anuario", dados=tmp_path / "inexistente")
