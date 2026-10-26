from decimal import Decimal

import pytest

from apps.importacao.normalizacao import Situacao, normalizar_celula


@pytest.mark.parametrize(
    ("bruto", "valor", "situacao"),
    [
        (42, Decimal(42), Situacao.INFORMADO),
        ("40.9", Decimal("40.9"), Situacao.INFORMADO),
        ("-", Decimal(0), Situacao.INEXISTENTE),
        ("...", None, Situacao.NAO_DISPONIVEL),
        ("", None, Situacao.NAO_DISPONIVEL),
        (None, None, Situacao.NAO_DISPONIVEL),
        (float("nan"), None, Situacao.NAO_DISPONIVEL),
    ],
)
def test_normalizar_celula(bruto, valor, situacao):
    celula = normalizar_celula(bruto)
    assert celula.valor == valor
    assert celula.situacao is situacao


def test_valor_desconhecido_gera_erro():
    with pytest.raises(ValueError, match="não reconhecido"):
        normalizar_celula("n/d")
