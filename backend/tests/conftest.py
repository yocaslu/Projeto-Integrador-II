"""Fixtures compartilhadas pelos testes do backend.

As planilhas reduzidas usadas nos testes de importação ficam em tests/fixtures/.
"""

from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR
