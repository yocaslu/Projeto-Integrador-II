# 0008. Cálculos da API no SQL: JIT desligado e índice das subconsultas

- Data: 2026-10-28
- Situação: aceita

## Contexto

O contrato (seção 3) e a regra 12 do CLAUDE.md pedem taxa, variação e participação calculadas no
SQL, por subconsulta (nunca por função de janela), em precisão total, para que a ordenação e a
paginação aconteçam no banco (regra 26). `apps/registros/queries.py` (`anotar_registros`) faz isso
com subconsultas correlacionadas: a população do ano, o mesmo registro no ano anterior (valor e
taxa) e o total do indicador e do pai.

Como `estado`, `regiao` e `recorte` são anuláveis e `NULL = NULL` não é verdadeiro em SQL, as
subconsultas comparam `COALESCE(campo, 0)`, o mesmo efeito do `NULLS NOT DISTINCT` da chave única.

Medido com a carga completa (1.980 registros), a consulta de todos os registros anotados e
ordenados levava 5,9 s. O `EXPLAIN ANALYZE` mostrou que 2,9 s eram compilação JIT do PostgreSQL,
disparada pelo custo estimado das subconsultas, e que a execução em si levava cerca de 0,3 s. O
`COALESCE` também impedia o uso dos índices existentes.

| Consulta | Original | JIT desligado | JIT desligado + índice |
| :--- | ---: | ---: | ---: |
| Todos os registros, ordenados | 5.859 ms | 359 ms | 283 ms |
| 1ª página de 100, por `-taxa` | — | 46 ms | 46 ms |
| BA, 2025, MVI | 44 ms | 13 ms | 13 ms |

## Decisão

1. **JIT desligado na conexão**: `DATABASES["default"]["OPTIONS"] = {"options": "-c jit=off"}`
   em `config/settings/base.py`, para todos os ambientes. O JIT compensa em consultas analíticas
   longas sobre muitas linhas; as da API são curtas, e a compilação custava dez vezes a execução.
   Há teste que confere `SHOW jit = off`.
2. **Índice funcional** `registro_chave_subconsultas` em `REGISTROS_ANUAIS`, com as mesmas
   expressões das subconsultas: `(COALESCE(estado_id, 0), COALESCE(regiao_id, 0), indicador_id,
   COALESCE(recorte_id, 0), unidade, ano)` (migração `registros/0002`). Hoje o ganho é modesto;
   com mais anos na base, evita que cada subconsulta percorra a tabela inteira.
3. **`taxa_origem` nula sempre que a taxa é nula.** O contrato diz que `origem` é nula quando
   `valor` é nulo, e que `taxa.valor` também é nulo quando não há denominador (ex.: total
   regional de feminicídio). Nos dois casos não existe taxa, e a origem fica nula; o mesmo vale,
   pelo contrato, para `taxa.fonte`.

## Consequências

- A anotação de todos os registros cabe com folga no RNF02 (p95 < 500 ms), que será medido no
  passo do teste de desempenho (ADR 0005), com serialização e HTTP incluídos.
- O JIT desligado vale também para o comando `importar_anuario`, cujas consultas são simples; o
  tempo da importação não mudou (cerca de 8 s, dominados pela leitura das planilhas).
- Qualquer subconsulta nova sobre `REGISTROS_ANUAIS` que compare localidade ou recorte deve usar
  `_chave()` de `queries.py`, para casar com o índice.
- Os valores anotados têm a precisão do `numeric` do PostgreSQL (divisão com pelo menos 16
  dígitos significativos). Na planilha versionada, taxa calculada, variação da taxa e
  participação batem com as publicadas até 1e-6 (testes em `tests/registros/test_anotacoes.py`).
