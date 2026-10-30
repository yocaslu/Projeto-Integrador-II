# 0009. Variação do Brasil em recortes com UFs que não informaram

- Data: 2026-10-29
- Situação: aceita

## Contexto

O Anuário publica as mortes decorrentes de intervenção policial também por corporação e situação
do policial (recortes da T08). Nem todas as UFs informam essa separação: as que não informam
aparecem com "..." (não disponível), e o total do Brasil publicado pelo FBSP soma apenas as UFs que
informaram (conferido em `agregacao.py`, que já anota esse fato na `observacao` do registro do
Brasil). Os totais regionais calculados pelo projeto não têm o problema, porque a região fica nula
quando falta alguma UF (regra 4).

O conjunto de UFs que informam muda de um ano para o outro e, principalmente, de uma edição do
Anuário para a seguinte. Na planilha de 2026, o Brasil em "Polícia Militar, em serviço" passa de
2.692 (2024) para 2.909 (2025), +8,06%, mas Sergipe só informa em 2025. Comparando as edições de
2025 e 2026 para o mesmo ano de 2024, o Brasil nesse recorte cai de 4.378 para 2.692, enquanto o
total de mortes quase não muda (6.243 para 6.237), porque BA, PA e RN deixaram de informar e AC, GO
e MS passaram a informar. A variação calculada sobre esses totais mede a troca de UFs, não o
fenômeno, e induziria a erro quem lê a série, no dashboard ou pela API.

Os valores por UF não têm o problema: cada UF informou ou está como "...", e as revisões entre
edições são pequenas.

## Decisão

1. **Os recortes continuam importados em todos os anos**, inclusive os de edições anteriores. O
   valor do Brasil é o publicado pelo FBSP (regra 4); quando há UFs sem informação, a
   `observacao` diz quantas informaram e quais faltam (já implementado na agregação).
2. **A variação do Brasil em um recorte é nula quando o conjunto de UFs que informaram muda entre
   os dois anos** (`variacao.valor_pct` e `variacao.taxa_pct`). A comparação exige conjunto
   idêntico, sem tolerância: qualquer UF que entra ou sai anula a variação. "Informar" é ter valor;
   "-" (fenômeno inexistente, valor 0) conta como informado e "..." não. É a diferença simétrica dos
   dois conjuntos, calculada por subconsulta em `apps/registros/queries.py`
   (`_conjunto_de_ufs_mudou`), como as demais (regra 12). A regra não vale para as UFs nem para os
   totais sem recorte.
3. **No dashboard** (fase do frontend): a evolução de um recorte é exibida por UF; no Brasil, o
   recorte aparece só como composição de um ano (a parcela de cada corporação no total). O total
   de letalidade segue normal em todos os níveis.

## Consequências

- Na carga atual, a variação de 2025 do Brasil fica nula em "Polícia Civil, em serviço" e
  "Polícia Militar, em serviço" (Sergipe passa a informar). Os recortes "fora de serviço" mantêm
  a variação.
- A mudança é compatível com a v1 (regra 22): nenhum campo muda de nome, tipo ou casas decimais, e
  o contrato já admitia `variacao` nula; acrescenta-se um caso documentado em `contrato-api.md`.
  O esquema OpenAPI não muda.
- Ordenar por `variacao_valor` ou `variacao_taxa` coloca esses registros entre os nulos, ao final.
- A subconsulta nova só roda nas linhas do Brasil com recorte (CASE externo) e compara
  localidade e recorte com `_chave()`, para usar o índice do ADR 0008; a anotação continua em uma
  única consulta. O custo que fica é o do **planejamento**: o Django repete a expressão em cada
  anotação que a usa (as duas variações e as duas versões arredondadas). Por isso a diferença
  simétrica é uma única subconsulta e a marcação entra por `alias()`, sem virar coluna. Medido na
  carga real (consulta de uma UF, ano e indicador): planejamento de 2,2 ms para 3,3 ms, com a
  execução inalterada (cerca de 1 ms); a primeira versão, com duas subconsultas e `annotate()`,
  chegava a 7,7 ms. p95 do teste do RNF02, `main` → esta mudança: `/registros/` 56 → 69 ms, CSV
  54 → 72 ms, `/ranking/` 57 → 58 ms, `/comparacao/` 105 → 155 ms, todos abaixo do limite de 500 ms.
- A participação (parcela da corporação no total) não muda: no mesmo ano, numerador e
  denominador vêm da mesma tabela e da mesma edição.
