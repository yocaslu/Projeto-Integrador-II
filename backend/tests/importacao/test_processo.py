"""Fluxo completo da importação sobre as planilhas reduzidas (tests/fixtures/planilhas/).

Com as abas T01, T02, T03, T08, T09, T15 e T21: 1.134 registros lidos (T02 462, T03 112, T08 280,
T15 168, T21 112) + 120 regionais calculados = 1.254, e 66 populações.
"""

from decimal import Decimal

import pytest

from apps.catalogo.models import Fonte, Recorte
from apps.importacao.erros import ErroImportacao
from apps.importacao.models import Carga
from apps.importacao.processo import importar, ler_manifesto, verificar_arquivos, versao_da_carga
from apps.importacao.validacao import Severidade
from apps.localidades.models import Populacao
from apps.registros.escolhas import Metodo, Situacao
from apps.registros.models import RegistroAnual
from tests.conftest import TABELAS_REDUZIDAS

pytestmark = pytest.mark.django_db

LIDOS, CALCULADOS = 1134, 120


def executar(planilhas, **opcoes):
    return importar(
        planilhas.dados,
        planilhas.relatorio,
        planilhas.manifesto,
        tabelas=TABELAS_REDUZIDAS,
        **opcoes,
    )


def test_importa_registros_populacao_e_relatorio(planilhas):
    resultado = executar(planilhas)

    assert (resultado.registros, resultado.calculados, resultado.populacao) == (
        LIDOS + CALCULADOS,
        CALCULADOS,
        66,
    )
    assert RegistroAnual.objects.count() == LIDOS + CALCULADOS
    assert RegistroAnual.objects.filter(metodo=Metodo.SOMA_UFS).count() == CALCULADOS
    assert Populacao.objects.count() == 66
    assert Recorte.objects.count() == 4
    assert not resultado.relatorio.tem_divergencias

    carga = Carga.objects.atual()
    assert carga == resultado.carga
    assert carga.status == Carga.Status.CONCLUIDA
    assert carga.total_registros == LIDOS + CALCULADOS
    assert {a["nome"] for a in carga.arquivos} == {p.name for p in planilhas.dados.iterdir()}
    assert all(caminho.is_file() for caminho in resultado.arquivos_relatorio)


def test_regioes_sem_dado_ficam_nao_disponiveis(planilhas):
    executar(planilhas)

    nulas = RegistroAnual.objects.filter(metodo=Metodo.SOMA_UFS, situacao=Situacao.NAO_DISPONIVEL)
    assert nulas.count() == 24  # 4 recortes da T08 × 2 anos × N, NE e SE
    assert set(nulas.values_list("regiao__sigla", flat=True)) == {"N", "NE", "SE"}
    sudeste = RegistroAnual.objects.get(
        regiao__sigla="SE", indicador__slug="homicidio-doloso", unidade="vitimas", ano=2025
    )
    assert sudeste.taxa_publicada is None
    assert sudeste.origem.startswith("T03!")
    assert "MG:" in sudeste.observacao


def test_importacao_idempotente(planilhas):
    executar(planilhas)
    antes = dict(RegistroAnual.objects.values_list("id", "valor"))

    executar(planilhas)

    assert dict(RegistroAnual.objects.values_list("id", "valor")) == antes
    assert Populacao.objects.count() == 66
    assert Carga.objects.filter(status=Carga.Status.CONCLUIDA).count() == 2


def test_somente_validar_nao_grava_nada(planilhas):
    resultado = executar(planilhas, somente_validar=True)

    assert resultado.carga is None
    assert resultado.registros == LIDOS + CALCULADOS
    assert not RegistroAnual.objects.exists()
    assert not Fonte.objects.exists()
    assert not Carga.objects.exists()
    assert all(caminho.is_file() for caminho in resultado.arquivos_relatorio)


def test_celula_invalida_desfaz_tudo_e_marca_a_carga(planilhas):
    planilhas.alterar_celula("T03", "C12", "n/d")

    with pytest.raises(ErroImportacao, match=r"T03!C12"):
        executar(planilhas)

    assert not RegistroAnual.objects.exists()
    assert not Populacao.objects.exists()
    assert Carga.objects.get().status == Carga.Status.FALHOU
    assert Carga.objects.atual() is None


def test_agregado_publicado_divergente_aborta(planilhas):
    planilhas.alterar_celula("T03", "B10", 1)  # Brasil de homicídio doloso, vítimas, 2024

    with pytest.raises(ErroImportacao, match="divergem da soma das UFs"):
        executar(planilhas)
    assert not RegistroAnual.objects.exists()


def test_taxa_divergente_entra_no_relatorio(planilhas):
    planilhas.alterar_celula("T03", "D10", 99.5)  # taxa do Brasil, vítimas, 2024

    resultado = executar(planilhas)

    [divergencia] = resultado.relatorio.de(Severidade.DIVERGENCIA)
    assert divergencia.origem == "T03!D10"
    assert divergencia.esperado == Decimal("99.500000000000")


def test_hash_divergente_aborta_antes_de_gravar(planilhas):
    planilhas.planilha.write_bytes(planilhas.planilha.read_bytes() + b"\0")

    with pytest.raises(ErroImportacao, match="SHA-256 de anuario-reduzido.xlsx"):
        executar(planilhas)
    assert not Carga.objects.exists()


def test_arquivo_do_manifesto_ausente_aborta(planilhas):
    (planilhas.dados / "POP2025_reduzido.ods").unlink()

    with pytest.raises(ErroImportacao, match="não encontrado"):
        verificar_arquivos(planilhas.dados, planilhas.manifesto)


def test_registro_orfao_nao_e_apagado_e_vira_aviso(planilhas):
    executar(planilhas)
    existente = RegistroAnual.objects.filter(estado__sigla="BA", ano=2025).first()
    existente.pk, existente.ano = None, 2011
    existente.save()

    resultado = executar(planilhas)

    assert RegistroAnual.objects.filter(ano=2011).exists()
    [aviso] = resultado.relatorio.de(Severidade.AVISO)
    assert aviso.verificacao == "registro_orfao"
    assert "BA" in aviso.obtido and "2011" in aviso.obtido


def test_manifesto_e_versao(planilhas):
    hashes = ler_manifesto(planilhas.manifesto)
    arquivos = verificar_arquivos(planilhas.dados, planilhas.manifesto)

    assert set(hashes) == {a.nome for a in arquivos}
    assert len(versao_da_carga(arquivos)) == 12
    assert versao_da_carga(arquivos) == versao_da_carga(list(reversed(arquivos))[::-1])


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_banco_limpo_reproduz_os_ids_do_contrato(planilhas):
    executar(planilhas)

    assert list(Fonte.objects.order_by("id").values_list("id", "slug")) == [
        (1, "secretarias-seguranca"),
        (2, "ibge-estimativas"),
        (3, "ibge-projecoes"),
        (4, "senatran-frota"),
        (5, "bcb-instituicoes"),
    ]
    # Recortes na ordem dos blocos da T08 em mapeamento.py (contrato, 4.4).
    assert list(Recorte.objects.order_by("id").values_list("id", "rotulo")) == [
        (1, "Polícia Civil, em serviço"),
        (2, "Polícia Militar, em serviço"),
        (3, "Polícia Civil, fora de serviço"),
        (4, "Polícia Militar, fora de serviço"),
    ]
