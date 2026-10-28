"""Campos decimais do contrato da API (contrato, seção 1.2).

Todos os números saem como texto, para preservar o NUMERIC (RNF10), e o arredondamento acontece
só aqui, na serialização (CLAUDE.md, regra 25): `apps/registros/queries.py` devolve precisão
total. O modo é meio para longe do zero (`ROUND_HALF_UP`), o mesmo do `round()` do PostgreSQL
para `numeric`. Zero negativo nunca aparece: `-0.004` sai como `"0.00"`.

| Campo | Formato | Exemplo |
| :--- | :--- | :--- |
| `CampoInteiro` | sem casas (vítimas, ocorrências, população) | `"5800"` |
| `CampoDuasCasas` | 2 casas fixas (taxa, variação, participação) | `"-3.10"` |
| `CampoPrecisaoGuardada` | até 12 casas, sem zeros à direita (`taxa_publicada`) | `"40.9415826"` |
"""

from decimal import ROUND_HALF_UP, Decimal

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

UNIDADE = Decimal(1)
DUAS_CASAS = Decimal("0.01")
DOZE_CASAS = Decimal("1e-12")


def _decimal(valor: Decimal | int) -> Decimal:
    """Aceita só Decimal e int; float perderia a precisão do NUMERIC (CLAUDE.md, regra 10)."""
    if isinstance(valor, bool) or not isinstance(valor, Decimal | int):
        raise TypeError(f"Esperado Decimal ou int, recebido {type(valor).__name__}: {valor!r}")
    return valor if isinstance(valor, Decimal) else Decimal(valor)


def _arredondar(valor: Decimal | int | None, exemplo: Decimal) -> Decimal | None:
    if valor is None:
        return None
    arredondado = _decimal(valor).quantize(exemplo, rounding=ROUND_HALF_UP)
    return abs(arredondado) if arredondado.is_zero() else arredondado


def arredondar_2(valor: Decimal | int | None) -> Decimal | None:
    """Arredonda a 2 casas, meio para longe do zero, sem zero negativo."""
    return _arredondar(valor, DUAS_CASAS)


def arredondar_inteiro(valor: Decimal | int | None) -> Decimal | None:
    """Arredonda a inteiro, meio para longe do zero, sem zero negativo."""
    return _arredondar(valor, UNIDADE)


def formatar_inteiro(valor: Decimal | int | None) -> str | None:
    """`Decimal("5800.0000")` → `"5800"`."""
    arredondado = arredondar_inteiro(valor)
    return None if arredondado is None else f"{arredondado:f}"


def formatar_duas_casas(valor: Decimal | int | None) -> str | None:
    """`Decimal("40.9415826")` → `"40.94"`; `Decimal("-3.1")` → `"-3.10"`."""
    arredondado = arredondar_2(valor)
    return None if arredondado is None else f"{arredondado:f}"


def formatar_precisao_guardada(valor: Decimal | int | None) -> str | None:
    """Até 12 casas, sem zeros à direita e sem notação exponencial.

    `Decimal("40.941582600000")` → `"40.9415826"`; `Decimal("0E-12")` → `"0"`;
    `Decimal("100.000000000000")` → `"100"` (e não `"1E+2"`, que `normalize()` sozinho daria).
    """
    arredondado = _arredondar(valor, DOZE_CASAS)
    if arredondado is None:
        return None
    return f"{arredondado.normalize():f}"


class _CampoDecimalTexto(serializers.Field):
    """Base dos campos somente leitura que serializam um decimal como texto."""

    def __init__(self, **kwargs):
        kwargs.setdefault("read_only", True)
        super().__init__(**kwargs)

    def formatar(self, valor: Decimal | int) -> str:
        raise NotImplementedError

    def to_representation(self, value):
        return None if value is None else self.formatar(value)


@extend_schema_field({"type": "string", "pattern": r"^-?\d+$", "example": "5800"})
class CampoInteiro(_CampoDecimalTexto):
    """Valor absoluto (vítimas, ocorrências) e população: inteiro, sem casas."""

    def formatar(self, valor):
        return formatar_inteiro(valor)


@extend_schema_field({"type": "string", "pattern": r"^-?\d+\.\d{2}$", "example": "40.94"})
class CampoDuasCasas(_CampoDecimalTexto):
    """Taxa, variação e participação: 2 casas fixas."""

    def formatar(self, valor):
        return formatar_duas_casas(valor)


@extend_schema_field(
    {"type": "string", "pattern": r"^-?\d+(\.\d{1,12})?$", "example": "40.9415826"}
)
class CampoPrecisaoGuardada(_CampoDecimalTexto):
    """`taxa_publicada`: a precisão guardada no banco (até 12 casas), sem zeros à direita."""

    def formatar(self, valor):
        return formatar_precisao_guardada(valor)
