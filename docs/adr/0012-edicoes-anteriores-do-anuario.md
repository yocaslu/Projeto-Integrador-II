# 0012. Edições anteriores do Anuário

- Data: 2026-10-30
- Situação: aceita

## Contexto

A edição de 2026 só traz 2024 e 2025, fora a série de MVI, então os demais indicadores tinham só dois
pontos no gráfico de evolução. As edições de 2025 e 2024 trazem 2023 e 2022, mas o mesmo ano aparece
em duas edições, às vezes com valores diferentes, e a numeração das tabelas muda.

## Decisão

1. **Edição dona:** cada (indicador, recorte, unidade, ano) vem, em todas as localidades, da edição
   mais recente cuja tabela traz esse ano: 2024 e 2025 da edição de 2026, 2023 da de 2025 e 2022 da
   de 2024. A dona nunca é escolhida por localidade: "..." e "-" contam como publicados, e o Brasil e
   as UFs saem sempre da mesma edição, para o Brasil continuar igual à soma das UFs que informaram.
2. **Revisões:** o mesmo dado em edição anterior nunca substitui o da dona. Se difere, a linha da dona
   recebe o valor anterior na `observacao`, inclusive quando traz "...", e o relatório registra uma
   informação. Regiões calculadas não recebem nota.
3. **MVI:** vem só da T02 da edição de 2026; as séries das edições anteriores não são lidas. 2011 fica
   de fora: só a edição de 2024 o traz, sem taxa e com números aparentemente incompletos.
4. **Agregação e validação por edição,** antes de escolher a dona. A variação e as proporções
   publicadas são conferidas com as linhas da própria edição; as proporções de MDIP usam a MVI da
   própria tabela de conferência.
5. **Edição de 2024:** as taxas dela usam o Censo 2022 como denominador, nos dois anos. Por isso a
   diferença para `POPULACAO` é informação, não divergência, e a taxa por habitante de 2022 é
   calculada com as Projeções (ADR 0011), com a publicada em `taxa_publicada`.
6. **Taxa por 100 mil mulheres:** `variacao.taxa_pct` de 2023 é nula, porque a taxa publicada de 2022
   usa o Censo e a de 2023, as Projeções. O denominador implícito salta 3,7% na mediana das localidades
   (0,4% de 2023 para 2024, no Brasil), e o feminicídio sobe 1,37% em valor enquanto a taxa cai 2,27%.
   `valor_pct` não muda. As bases de veículos e instituições não têm esse salto.
7. **Origem:** linhas das edições anteriores levam o nome do arquivo (`anuario-2025.xlsx:T09!D15`);
   sem prefixo, a origem é a edição atual.

## Consequências

- `REGISTROS_ANUAIS` passa de 1.980 para 3.498 registros (3.038 lidos e 460 regionais), e os
  indicadores além da MVI têm 4 pontos.
- A variação segue calculada entre anos de edições diferentes, porque a edição de 2026 não traz 2023.
  As revisões podem ser grandes: em 490 comparações de totais por UF, 28 mudam mais de 10 pontos
  percentuais e 8 invertem o sinal (roubo a estabelecimento comercial no PA, 2024: 740 na edição de
  2025 e 2.035 na de 2026). Isso corrige a afirmação do ADR 0009 de que as revisões por UF são
  pequenas, e a nota na `observacao` deixa a revisão visível.
- O relatório cresce: 613 revisões e 780 comparações de taxa da edição de 2024 como informação.
- A regra da variação do Brasil em recortes (ADR 0009) passa a anular também as variações entre
  edições quando o conjunto de UFs muda, como previsto.
