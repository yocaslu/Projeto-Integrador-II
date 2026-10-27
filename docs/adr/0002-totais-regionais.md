# 0002. Totais regionais calculados como soma das UFs

- Data: 2026-10-27
- Situação: aceita

## Contexto

O RF13 pede comparar uma UF com sua região e com o Brasil, e o `/comparacao/` devolve as três
séries. A planilha do FBSP publica o Brasil em todas as tabelas, mas as regiões só na série
histórica de MVI (T02). Importando apenas o que é publicado, a série regional existiria só para
a MVI, e a comparação ficaria incompleta para letalidade policial, feminicídio, roubo e furto.

O Roteiro (Modelagem de dados) já previa calcular esses totais como soma das UFs, com o atributo
`metodo` para distinguir o valor publicado do calculado. A especificação da importação e o
CLAUDE.md diziam o contrário ("agregados importados, nunca somados"), e a divergência foi
resolvida em favor do Roteiro.

Conferência feita na planilha versionada: em todas as colunas de números absolutos das tabelas
lidas, o Brasil é exatamente a soma das UFs, e cada região da T02 é exatamente a soma de suas
UFs, de 2012 a 2025. Logo, a soma reproduz o método do FBSP.

## Decisão

- Nas tabelas que não publicam regiões, a importação calcula o total de cada região como a soma
  das UFs, gravado com `metodo = soma_ufs`. Os valores lidos da planilha têm `metodo = publicado`.
- A soma vale só para números absolutos, dentro do mesmo indicador, recorte e ano. Nunca entre
  um indicador e seus subtipos, e nunca como média de taxas.
- Se alguma UF da região não informa o dado, o total regional é `nao_disponivel`, e não uma
  soma parcial.
- A taxa regional é calculada com a população da região quando a base é 100 mil habitantes; nas
  demais bases, é nula.
- Os agregados publicados (Brasil em todas as tabelas, regiões na T02) passam a ser conferidos
  contra a soma das UFs, e uma divergência interrompe a importação.
- A API expõe `metodo` em cada registro, para que o dashboard identifique os valores calculados.

## Consequências

- `/comparacao/` e `nivel=regiao` passam a ter dados para todos os indicadores do escopo.
- A carga passa de 1.582 para 1.782 registros (200 `soma_ufs`, dos quais 24 `nao_disponivel`
  nos recortes da T08).
- `REGISTROS_ANUAIS` ganha o campo `metodo`; `taxa_publicada` fica nula nos registros
  `soma_ufs`. (Corrigido em 2026-10-27: `origem` não é nula, lista as células somadas, e
  `observacao` traz as notas das UFs, como já fazem `agregacao.py` e seus testes; ver
  `docs/importacao.md`, seção 4.8.)
- Os totais regionais de feminicídio, homicídio de mulheres, roubo e furto de veículo e roubo a
  instituição financeira ficam sem taxa, por falta de denominador regional.
- O Brasil dos recortes da T08 é uma soma parcial publicada pelo FBSP (há UFs com "..."). Ele é
  importado como está, mas convive com regiões `nao_disponivel` no mesmo recorte; o relatório
  registra o caso.
- A conferência que aborta protege contra mudanças de método em edições futuras da planilha.
