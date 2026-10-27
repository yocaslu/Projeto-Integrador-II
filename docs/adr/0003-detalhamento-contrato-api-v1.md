# 0003. Detalhamento do contrato da API v1

- Data: 2026-10-27
- Situação: aceita

## Contexto

A seção "Contrato da API" do Roteiro define recursos, filtros e o formato dos registros, mas
deixava em aberto pontos que, sem decisão, viram escolhas feitas no código de cada serializer:
o formato de resposta dos demais recursos; os parâmetros de `/ranking/` e `/comparacao/`; as
siglas e os códigos IBGE das regiões e do Brasil; as casas decimais (pendência 4 do CLAUDE.md);
a posição do feminicídio na hierarquia (pendência 3); o comportamento de `/registros/` sem
`nivel`; os campos de ordenação; e as colunas do CSV. Qualquer um desses pontos, mudado depois de
publicado, quebra a v1.

## Decisão

O detalhamento completo está em `docs/contrato-api.md`, que passa a ser a fonte da verdade da
API. Em resumo:

1. **Formatos:** catálogos devolvem array JSON na raiz; `/ranking/`, `/comparacao/` e
   `/metadados/` devolvem objeto com os parâmetros usados ecoados; `/registros/` e `/populacao/`
   mantêm o envelope paginado `count`/`next`/`previous`/`results`. Campos nunca são omitidos:
   ausência = `null`.
2. **Ranking:** `indicador` obrigatório; `ano` padrão = último ano com dados do indicador;
   `criterio` padrão `taxa`; `recorte` padrão `total` ou um id. Só as 27 UFs.
   **Comparação:** `uf` e `indicador` obrigatórios; `ano_min`/`ano_max` padrão = anos do
   indicador; `recorte` padrão `total` ou um id.
3. **Localidades:** siglas `BR`, `N`, `NE`, `SE`, `S`, `CO`; `codigo_ibge` em texto, com os
   códigos reais do IBGE (Brasil `1`, regiões `1` a `5`, UFs de 2 dígitos). A identidade é sempre
   (`nivel`, `codigo`); unicidade de `REGIOES.codigo_ibge` por `tipo`.
4. **Decimais:** valores absolutos inteiros; `taxa.valor` e variações com 2 casas fixas;
   `taxa_publicada` com a precisão guardada. Arredondamento meio para longe do zero, só na
   serialização; `queries.py` devolve precisão total. Ordenação e ranking usam o valor arredondado.
   `taxa_publicada` é guardada com 12 casas (`NUMERIC(24, 12)`), arredondada na importação. A
   planilha traz até 17 dígitos significativos (até 18 casas), ruído do ponto flutuante do Excel;
   guardar tudo exigiria 18 casas. Aceita-se o erro de até 5e-13, irrelevante para a análise, em
   troca de não reproduzir a célula dígito a dígito.
5. **Hierarquia:** `homicidio-doloso` → `homicidio-mulheres` → `feminicidio`. A hierarquia
   significa "contido em", nunca "soma de". `INDICADORES` ganha `ordem` (pré-ordem).
6. **Nível:** sem `nivel`, a resposta tem um nível só (`uf` por padrão); misturar níveis exige
   lista explícita (`nivel=pais,regiao,uf`). `regiao` sem `nivel` é ambíguo → 400; `uf` com nível
   diferente de `uf` → 400; `uf` e `regiao` são mutuamente exclusivos.
7. **Ordenação:** `ano`, `indicador`, `localidade`, `recorte`, `valor`, `taxa`, `variacao_valor`,
   `variacao_taxa`; padrão `indicador, localidade, recorte, ano`; desempate final por `id`; nulos
   ao final; taxa e variação anotadas no SQL. (Atualizado em 2026-10-27 pelo ADR 0004: a lista
   inclui também `unidade` e `participacao`, e o padrão passa a `indicador, localidade, recorte,
   unidade, ano`; participação também anotada no SQL. A lista vigente é a do contrato, 4.7.3.)
8. **CSV:** em `/registros/`, `/populacao/`, `/ranking/` e `/comparacao/`; RFC 4180, UTF-8 sem
   BOM; colunas fixas, achatadas por `_`. `formato` é parâmetro reservado em todos os recursos;
   `pagina`/`tamanho` só nos paginados e só em JSON.

## Consequências

- Os serializers e filtros têm especificação verificável; a seção 8 do contrato lista os testes.
- Migrações: `INDICADORES.ordem`; `codigo_ibge` em `ESTADOS` e `REGIOES` como `CharField(2)`,
  com unicidade (`tipo`, `codigo_ibge`) em `REGIOES`.
- `apps/registros/queries.py` deixa de arredondar a variação a 4 casas (o teste correspondente
  muda); o arredondamento passa a um campo de serializer próprio (`apps/api/v1/campos.py`).
- O relatório de validação não distingue diferenças menores que 5e-13 entre a taxa calculada e a
  publicada (hoje elas são da ordem de 1e-14); com a tolerância sugerida de 1e-6 (pendência 5),
  isso não muda nenhum resultado.
- `docs/importacao.md` (seção 2) e `catalogo/referencia.py` passam a ter `feminicidio` como filho
  de `homicidio-mulheres`.
- `Vary: Accept` e ETag por representação passam a ser exigidos, porque a mesma URL serve JSON e
  CSV.
- O ranking por região, a filtragem por `uf` no ranking e o `ano` em `/comparacao/` ficam fora da
  v1; podem entrar depois como parâmetros opcionais sem quebrar o contrato.
