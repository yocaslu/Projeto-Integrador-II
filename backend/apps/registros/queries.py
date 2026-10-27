"""Consultas reutilizadas pelos endpoints /registros/, /ranking/ e /comparacao/.

Ficam fora das views para que os cálculos sejam testados sem requisições HTTP.
"""

from decimal import Decimal


def variacao_percentual(atual: Decimal | None, anterior: Decimal | None) -> Decimal | None:
    """Variação percentual entre dois anos.

    É nula quando falta um dos valores ou quando a base é zero, como define o contrato da API.
    Devolve precisão total: o arredondamento a 2 casas acontece só na serialização
    (apps/api/v1/campos.py; contrato, seção 1.2).
    Na consulta ao banco, o mesmo cálculo é feito por subconsulta sobre o ano anterior, e não
    por função de janela, para que um filtro como ano=2025 não deixe a variação sempre nula.
    """
    if atual is None or anterior is None or anterior == 0:
        return None
    return (atual - anterior) / anterior * 100


def posicoes_com_empate(valores: list[Decimal | None]) -> list[int | None]:
    """Posições no ranking, em ordem decrescente, com empates na mesma posição (1, 2, 2, 4).

    Valores nulos (dado não disponível) recebem posição nula.
    """
    ordenados = sorted((v for v in valores if v is not None), reverse=True)
    primeira_posicao: dict[Decimal, int] = {}
    for indice, valor in enumerate(ordenados, start=1):
        primeira_posicao.setdefault(valor, indice)
    return [None if v is None else primeira_posicao[v] for v in valores]
