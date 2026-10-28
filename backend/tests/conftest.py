"""Fixtures compartilhadas pelos testes do backend.

As planilhas reduzidas usadas nos testes de importação ficam em tests/fixtures/planilhas/ e são
geradas por tests/fixtures/gerar_planilhas.py: as abas T01, T02, T03, T08, T09, T15 e T21 da
planilha do FBSP, com todas as linhas, e só a aba BRASIL_E_UFs das estimativas do IBGE.
"""

import shutil
from pathlib import Path

import pytest

from apps.importacao.mapeamento import TABELAS
from apps.importacao.processo import sha256

FIXTURES_DIR = Path(__file__).parent / "fixtures"
PLANILHAS_DIR = FIXTURES_DIR / "planilhas"
ABAS_REDUZIDAS = ("T01", "T02", "T03", "T08", "T09", "T15", "T21")
TABELAS_REDUZIDAS = tuple(t for t in TABELAS if t.aba in ABAS_REDUZIDAS)


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR


class Planilhas:
    """Cópia das planilhas reduzidas num diretório temporário, com o manifesto ao lado."""

    def __init__(self, raiz: Path):
        shutil.copytree(PLANILHAS_DIR, raiz, dirs_exist_ok=True)
        self.dados = raiz / "brutos"
        self.manifesto = raiz / "README.md"
        self.relatorio = raiz / "relatorios"
        self.planilha = self.dados / "anuario-reduzido.xlsx"

    def atualizar_manifesto(self) -> None:
        """Regrava os hashes depois de alterar uma planilha de propósito."""
        linhas = ["| Arquivo | Conteúdo | SHA-256 |", "| --- | --- | --- |"]
        for arquivo in sorted(self.dados.iterdir()):
            linhas.append(f"| `{arquivo.name}` | teste | `{sha256(arquivo)}` |")
        self.manifesto.write_text("\n".join(linhas) + "\n", encoding="utf-8")

    def alterar_celula(self, aba: str, coordenada: str, valor) -> None:
        import openpyxl

        wb = openpyxl.load_workbook(self.planilha)
        wb[aba][coordenada] = valor
        wb.save(self.planilha)
        self.atualizar_manifesto()


@pytest.fixture
def planilhas(tmp_path) -> Planilhas:
    return Planilhas(tmp_path / "planilhas")
