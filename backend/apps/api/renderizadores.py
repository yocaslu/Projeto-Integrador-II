"""Exportação em CSV (RF07).

Previsto:

- renderizador selecionado por formato=csv ou pelo cabeçalho Accept: text/csv;
- resposta por streaming (StreamingHttpResponse), limitada a 50 mil linhas (acima disso, 400);
- colunas fonte e situacao em todas as linhas (RF11, RNF12), sem linhas de comentário.
"""

LIMITE_LINHAS_CSV = 50_000
