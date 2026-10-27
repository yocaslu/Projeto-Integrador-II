# 0004. Ocorrências, participação calculada, perfis de vítimas e tolerância da validação

- Data: 2026-10-27
- Situação: aceita

## Contexto

Quatro pendências do CLAUDE.md foram decididas pela equipe:

1. **Ocorrências.** As tabelas T03, T04 e T05 publicam, para homicídio doloso, latrocínio e lesão
   corporal seguida de morte, o número de vítimas e o de ocorrências (um fato pode ter mais de uma
   vítima), cada um com taxa por 100 mil habitantes e variação. Só vítimas era importado.
2. **Perfis de vítimas** (sexo, raça/cor, faixa etária). Só existem nos painéis P01, P03 e P06,
   em blocos de gráfico, apenas para o Brasil e em percentuais. Não há tabela por UF nem números
   absolutos que sustentem recortes comparáveis aos demais.
3. **Tolerância da validação.** `validacao.py` arredonda as taxas a 1 casa e tolera 0,1, embora as
   taxas do FBSP batam com o cálculo pela população do IBGE até ~1e-14.
4. **Proporções** (T09 e coluna "Proporção" da T21). Conferido na planilha: a T09 é
   MDIP ÷ MVI × 100 e a T21 é feminicídio ÷ homicídio de mulheres × 100, com os mesmos números
   absolutos da T02, da T08 e da própria T21. As duas são a participação de um indicador no seu
   indicador-pai.

Conferido também: no bloco de ocorrências de T03–T05 não há "..." nem "-", o Brasil é exatamente
a soma das UFs nos dois anos, e as taxas de ocorrências são por 100 mil habitantes e batem com a
população do IBGE. E a coluna "Variação (%)" de todas as tabelas é a **variação da taxa**, não a do
valor absoluto (Brasil, T03, vítimas: publicada −10,0305…, da taxa −10,0305…, dos absolutos
−9,676…); a especificação da validação dizia o contrário.

## Decisão

### 1. Ocorrências: a unidade passa a ser atributo do registro

- `REGISTROS_ANUAIS.unidade` (`vitimas` | `ocorrencias`) entra no registro e na chave única:
  (estado, regiao, indicador, recorte, **unidade**, ano), `NULLS NOT DISTINCT`.
- `INDICADORES.unidade` vira `INDICADORES.unidade_padrao`: a unidade usada quando o cliente não
  pede outra (vítimas para os crimes contra a vida, ocorrências para roubo e furto).
- Alternativa descartada: indicadores próprios (`homicidio-doloso-ocorrencias` etc.). Duplicaria o
  catálogo e quebraria a hierarquia (a MVI só existe em vítimas, então o "pai" das ocorrências de
  homicídio doloso não existiria).
- A taxa de ocorrências segue a regra 11 (base 100 mil habitantes → calculada pelo IBGE). A
  variação compara a mesma unidade. A soma regional (ADR 0002) vale para as duas unidades.
- Na API, `unidade` é parâmetro de `/registros/`, `/ranking/` e `/comparacao/`, com padrão
  `padrao` (a unidade padrão de cada indicador), pela mesma razão de `recorte=total`: nunca
  misturar vítimas e ocorrências do mesmo crime por omissão.

### 2. Perfis de vítimas fora do escopo

Não entram na base nem na API. O RF02 continua (é o requisito da própria API), com o texto do
recorte restrito às características dos agentes (corporação e situação do policial, T08). As
dimensões de recorte permitidas ficam `corporacao` e `situacao_policial`.

### 3. Validação sem arredondar, com tolerância absoluta de 1e-6

- Toda comparação do relatório (taxa, variação, participação, conferências entre tabelas) é feita
  em precisão total, sem arredondar nenhum lado, com `|calculado − publicado| ≤ 1e-6`.
- A variação publicada é comparada à variação **da taxa** (a mesma que a API expõe em
  `variacao.taxa_pct`).

### 4. Proporções como cálculo da API: `participacao`

- Não são importadas. Cada registro da API ganha o objeto `participacao`:
  - registro **sem recorte** de indicador com pai que tem registros → valor ÷ valor do
    indicador-pai × 100, na mesma localidade, ano e unidade, sem recorte (`tipo = indicador_pai`);
  - registro **com recorte** → valor ÷ valor do total do mesmo indicador × 100, na mesma
    localidade, ano e unidade (`tipo = total_do_indicador`);
  - nos demais casos (indicador-raiz, pai agrupador sem registros), referência e valor nulos.
- Calculada no SQL por subconsulta (como a variação), em precisão total, arredondada a 2 casas na
  serialização. Disponível em `ordenar=participacao` e no ranking (`criterio=participacao`).
- A T09 e a coluna de proporção da T21 passam a ser **conferências** no relatório: a participação
  calculada é comparada à publicada, e os absolutos da T09 aos da T02 e da T08.

## Consequências

- Migração: `unidade` em `RegistroAnual` (na chave única) e `unidade_padrao` em `Indicador`.
  `linhas.Chave` ganha `unidade`, e `agregacao.agregar` passa a decidir o que é somável pela
  unidade da chave, não pela do indicador.
- Carga: 1.980 registros (1.750 lidos + 230 regionais calculados, dos quais 24 nulos). Antes:
  1.782.
- Contrato: `unidade` sai do objeto `indicador` e vai para o registro; `/indicadores/` troca
  `unidade` por `unidade_padrao` e `unidades`; novo objeto `participacao`; colunas novas no CSV.
  Como a v1 ainda não foi publicada, nada disso exige `/api/v2/`.
- A unidade `percentual` deixa de existir: nenhum registro é percentual, e a única grandeza
  percentual da API é calculada (`participacao`).
- A soma das participações dos subtipos não fecha 100% (uma ocorrência pode estar em mais de um
  subtipo de roubo; o total de roubo é menor que a soma dos subtipos). O contrato avisa que elas
  não devem ser somadas.
- Em algumas UFs uma unidade foi preenchida com a outra, por falta do dado: PI, RJ, RN e RR têm
  ocorrências iguais às vítimas (T03 nota 5, T04 nota 3, T05 nota 3), e SP tem vítimas de lesão
  corporal seguida de morte iguais às ocorrências (T05 nota 5). Essas notas vão para `observacao`
  (RF11), e as somas regionais as herdam com a sigla da UF.
- Validação mais estrita: qualquer diferença real acima de 1e-6 aparece no relatório.
