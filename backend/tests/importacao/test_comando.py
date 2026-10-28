from functools import partial
from io import StringIO

import pytest
from django.core.management import CommandError, call_command

from apps.importacao import processo
from apps.registros.models import RegistroAnual
from tests.conftest import TABELAS_REDUZIDAS


@pytest.fixture
def com_tabelas_reduzidas(monkeypatch):
    """O comando usa o mapeamento completo; nos testes, só as abas das planilhas reduzidas."""
    monkeypatch.setattr(
        "apps.importacao.management.commands.importar_anuario.importar",
        partial(processo.importar, tabelas=TABELAS_REDUZIDAS),
    )


def comando(planilhas, *opcoes):
    saida = StringIO()
    call_command(
        "importar_anuario",
        "--dados",
        str(planilhas.dados),
        "--relatorio",
        str(planilhas.relatorio),
        "--manifesto",
        str(planilhas.manifesto),
        *opcoes,
        stdout=saida,
    )
    return saida.getvalue()


def test_comando_falha_sem_diretorio(tmp_path):
    with pytest.raises(CommandError, match="não encontrado"):
        call_command("importar_anuario", dados=tmp_path / "inexistente")


@pytest.mark.django_db
def test_comando_importa_e_resume(planilhas, com_tabelas_reduzidas):
    saida = comando(planilhas)

    assert "anuario-reduzido.xlsx" in saida
    assert "1254 registros (120 regionais calculados) e 66 populações" in saida
    assert "Nenhuma divergência" in saida
    assert RegistroAnual.objects.count() == 1254


@pytest.mark.django_db
def test_comando_somente_validar(planilhas, com_tabelas_reduzidas):
    saida = comando(planilhas, "--somente-validar")

    assert "validada (nada gravado)" in saida
    assert not RegistroAnual.objects.exists()


@pytest.mark.django_db
def test_estrito_falha_com_divergencia(planilhas, com_tabelas_reduzidas):
    planilhas.alterar_celula("T03", "D10", 99.5)

    assert "1 divergência(s)" in comando(planilhas)
    with pytest.raises(CommandError, match="1 divergência"):
        comando(planilhas, "--estrito")


@pytest.mark.django_db
def test_erro_de_importacao_vira_command_error(planilhas, com_tabelas_reduzidas):
    planilhas.alterar_celula("T03", "C12", "n/d")

    with pytest.raises(CommandError, match=r"Importação desfeita: T03!C12"):
        comando(planilhas)


def test_inspecionar_planilha(planilhas):
    saida = StringIO()
    call_command("inspecionar_planilha", "T03", planilha=planilhas.planilha, stdout=saida)
    texto = saida.getvalue()

    assert "âncora na linha 5" in texto
    assert "('Homicídios dolosos', 'Nº de Vítimas', 'Taxas (2)', '2024 (3)')" in texto
    assert "todas as colunas resolvidas" in texto


def test_inspecionar_aba_inexistente(planilhas):
    with pytest.raises(CommandError, match="Aba T04 não encontrada"):
        call_command("inspecionar_planilha", "T04", planilha=planilhas.planilha, stdout=StringIO())
