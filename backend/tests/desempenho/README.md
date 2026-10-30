# Testes de desempenho

Testes do RNF02: a API deve responder em menos de 500 ms em 95% das consultas filtradas por UF,
ano e indicador. O método foi decidido no ADR 0005 (seção 4); este resumo não o substitui.

- **Arquivo:** `test_p95.py`, com o marker `desempenho`. Fica fora da execução padrão e roda em
  passo próprio do CI: `uv run pytest -m desempenho --no-cov`.
- **Banco:** a carga real completa (1.980 registros e 462 linhas de população), importada uma vez
  por sessão pelo `importar_anuario` a partir de `dados/brutos/` (fixture `carga_real`, em
  `conftest.py`) e apagada no fim.
- **Cliente:** `django.test.Client`, em processo, sem `If-None-Match`; no CSV, o streaming é
  consumido por inteiro dentro da medição.
- **Consultas** com `mvi`, `homicidio-doloso`, `feminicidio`, `morte-intervencao-policial` e
  `roubo`:
  - `/registros/?uf=&ano=&indicador=`: 27 UFs × 2 anos × 5 indicadores = 270;
  - o mesmo com `formato=csv`: 270;
  - `/ranking/?indicador=&ano=`: 5 × 2, três vezes = 30;
  - `/comparacao/?uf=&indicador=`: 27 × 5 = 135.
- **Aquecimento:** 20 requisições por recurso, descartadas.
- **Critério:** toda resposta 200 e p95 de cada recurso < 500 ms
  (`statistics.quantiles(tempos, n=20, method="inclusive")[18]`); a falha mostra p50, p95 e máximo.
- Uma requisição de cada recurso também passa por `django_assert_max_num_queries`.
