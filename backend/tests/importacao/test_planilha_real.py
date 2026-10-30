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

    assert (resultado.registros, resultado.calculados, resultado.populacao) == (3498, 460, 462)
    assert not resultado.relatorio.tem_divergencias
    assert resultado.relatorio.conferidos["taxa_calculada_x_publicada"] == 1246
    # A dona de cada ano (ADR 0012): 2022 da edição de 2024, 2023 da de 2025, 2024 da de 2026.
    registro = RegistroAnual.objects.filter(estado__sigla="SP", indicador__slug="latrocinio")
    registro = registro.filter(unidade="vitimas", recorte__isnull=True)
    origens = {r.ano: r.origem.split("!")[0] for r in registro}
    assert origens == {
        2022: "anuario-2024.xlsx:T05",
        2023: "anuario-2025.xlsx:T04",
        2024: "T04",
        2025: "T04",
    }
    # "..." na edição dona continua "...", com o número da edição anterior na observação.
    bahia = RegistroAnual.objects.get(
        estado__sigla="BA",
        indicador__slug="morte-intervencao-policial",
        recorte__chave__contains="Polícia Militar;situacao_policial=Em serviço",
        ano=2024,
    )
    assert bahia.valor is None
    assert "edição de 2025 do Anuário publicou 1496" in bahia.observacao
    regionais = Counter(
        RegistroAnual.objects.filter(metodo=Metodo.SOMA_UFS).values_list("situacao", flat=True)
    )
    assert regionais[Situacao.NAO_DISPONIVEL] == 59
    assert sum(regionais.values()) == 460
