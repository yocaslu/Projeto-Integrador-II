"""Importação da planilha real de dados/brutos/ (docs/importacao.md, seção 6).

Fora da execução padrão; rode com `uv run pytest -m planilha_real --no-cov`.
"""

from collections import Counter
from pathlib import Path

import pytest
from django.conf import settings

from apps.importacao.leitores import fbsp
from apps.importacao.mapeamento import TABELAS
from apps.importacao.processo import importar
from apps.registros.escolhas import Metodo, Situacao
from apps.registros.models import RegistroAnual

pytestmark = [pytest.mark.planilha_real, pytest.mark.django_db]

DADOS = Path(settings.BASE_DIR).parent / "dados"


def test_toda_ancora_fica_na_linha_5():
    wb = fbsp.abrir(DADOS / "brutos" / "anuario-2026.xlsx")
    for tabela in TABELAS:
        grade = fbsp.Grade(wb[tabela.aba])
        assert fbsp.achar_ancora(grade, tabela.ancora, tabela.aba) == 5, tabela.aba


def test_carga_completa(tmp_path):
    resultado = importar(DADOS / "brutos", tmp_path, DADOS / "README.md")

    assert (resultado.registros, resultado.calculados, resultado.populacao) == (1980, 230, 462)
    assert not resultado.relatorio.tem_divergencias
    assert resultado.relatorio.conferidos["taxa_calculada_x_publicada"] == 1246
    regionais = Counter(
        RegistroAnual.objects.filter(metodo=Metodo.SOMA_UFS).values_list("situacao", flat=True)
    )
    assert regionais[Situacao.NAO_DISPONIVEL] == 24
    assert sum(regionais.values()) == 230
