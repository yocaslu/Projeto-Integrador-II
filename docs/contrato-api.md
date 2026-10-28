# Contrato da API — v1

Transcrição detalhada da seção "Contrato da API" do Roteiro, com as decisões que o Roteiro deixava
em aberto (ADRs 0003, 0004 e 0005). **Este arquivo é a fonte da verdade da API v1**: o Roteiro é o texto
acadêmico e resume o que está aqui. Se o código divergir deste documento, pare e pergunte antes de
mudar qualquer um dos lados.

Tudo o que está aqui faz parte do contrato da v1. Mudar nome, tipo, ordem de coluna do CSV,
número de casas decimais, valor padrão de parâmetro ou regra de validação de um jeito que quebre
um cliente exige `/api/v2/`. **Acrescentar** campo na resposta, parâmetro opcional ou recurso novo
é compatível e pode entrar na v1.

Com o ambiente no ar, a documentação gerada a partir do código fica em `/api/v1/docs/` (Swagger
UI), `/api/v1/redoc/` (ReDoc) e `/api/v1/schema/` (OpenAPI 3). O esquema versionado fica em
`docs/api/openapi.yaml`.

---

## 1. Convenções gerais

- **Prefixo e versão:** `/api/v1/`, com `URLPathVersioning`. A v1 continua no ar quando houver v2.
- **Métodos:** `GET`, `HEAD` e `OPTIONS`. Qualquer outro método → 405.
- **Nomes:** campos e parâmetros em português, `snake_case`, sem acento, iguais aos atributos do
  modelo quando existem.
- **Barra final:** todos os caminhos terminam em `/` (padrão do Django).
- **Formatos:** JSON (`application/json`) por padrão; CSV nos recursos da seção 5.
- **Nulos:** um campo do contrato **nunca é omitido**. Quando não há valor, ele vem como `null`
  (JSON) ou campo vazio (CSV). Objetos aninhados (`taxa`, `variacao`) também estão sempre
  presentes, com seus campos nulos.

### 1.1 Localidades: siglas e códigos

A identidade de uma localidade na API é o par **(`nivel`, `codigo`)**. A sigla sozinha é ambígua
(`SE` = Sergipe ou Sudeste), e o `codigo_ibge` também (`1` = Brasil no nível país ou Norte no
nível região).

| Nível | `codigo` (sigla) | `nome` | `codigo_ibge` |
| :--- | :--- | :--- | :--- |
| `pais` | `BR` | Brasil | `1` |
| `regiao` | `N` | Norte | `1` |
| `regiao` | `NE` | Nordeste | `2` |
| `regiao` | `SE` | Sudeste | `3` |
| `regiao` | `S` | Sul | `4` |
| `regiao` | `CO` | Centro-Oeste | `5` |
| `uf` | `AC`, `AL`, …, `TO` | nome oficial da UF | código de 2 dígitos do IBGE (`11` RO … `53` DF) |

- O Brasil fica em `REGIOES` com `tipo = pais`, sigla `BR`.
- `codigo_ibge` é **texto** (é identificador, não quantidade): `CharField(max_length=2)`.
  Unicidade em `REGIOES` por (`tipo`, `codigo_ibge`); em `ESTADOS`, `codigo_ibge` é único.
- Na saída, siglas sempre em maiúsculas. Na entrada (parâmetros e caminhos), siglas são aceitas
  sem diferença de caixa (`sp` = `SP`).
- **Ordem canônica de localidades**, usada em todas as listas: Brasil; regiões por
  `codigo_ibge` (N, NE, SE, S, CO); UFs por sigla (AC, AL, AM, AP, BA, …, TO).

### 1.2 Números decimais

Todos os números decimais saem como **texto**, para preservar o NUMERIC (RNF10); nunca `float`.
O arredondamento acontece **só na serialização**, em um único campo de serializer
(`apps/api/v1/campos.py`), e nunca em `queries.py`, que devolve precisão total. O modo de
arredondamento é **meio para longe do zero** (`ROUND_HALF_UP` do `decimal`, o mesmo do `round()`
do PostgreSQL para `numeric`).

| Campo | Formato | Exemplo |
| :--- | :--- | :--- |
| `valor` com unidade `vitimas` ou `ocorrencias` | inteiro, sem casas | `"5800"` |
| `participacao.valor_pct` | 2 casas fixas | `"16.19"` |
| `taxa.valor` | 2 casas fixas | `"40.94"` |
| `variacao.valor_pct`, `variacao.taxa_pct` | 2 casas fixas, sinal `-` quando negativa | `"-3.10"` |
| `taxa_publicada` | até 12 casas (a precisão guardada no banco), sem zeros à direita e sem notação exponencial | `"40.9415826"` |
| `populacao.valor` | inteiro, sem casas | `"213421037"` |

- Zero sai como `"0"` (inteiros) ou `"0.00"` (2 casas). Nunca `"-0.00"`: zero negativo vira
  `"0.00"`.
- `taxa_publicada` mantém as 12 casas guardadas para dar transparência ao relatório de validação
  (RF12); o cliente que quiser exibi-la arredonda. As 12 casas vêm do arredondamento feito na
  importação (a célula da planilha pode ter até 18 casas, ruído do ponto flutuante do Excel); a
  diferença é de no máximo 5e-13.
- **A API ordena e classifica pelo que mostra:** `ordenar=taxa`, `ordenar=participacao` e o
  ranking usam o valor já arredondado a 2 casas. Duas UFs que aparecem com `"40.94"` empatam.

---

## 2. Parâmetros de consulta: regras comuns

Valem para todos os recursos.

1. **Parâmetro desconhecido → 400.** Cada recurso aceita só os parâmetros listados na sua seção,
   mais os **reservados** abaixo. O erro lista cada parâmetro desconhecido em `erros`.
2. **Parâmetros reservados:**
   - `formato` (`json` | `csv`): aceito em todos os recursos. `formato=json` funciona em todos;
     `formato=csv` só nos recursos com CSV (seção 5); nos demais → 406. Qualquer outro valor → 406.
   - `pagina` e `tamanho`: aceitos **só** em `/registros/` e `/populacao/` e **só** em JSON.
     Em outro recurso, ou junto com CSV, → 400 (a exportação é sempre completa).
3. **Listas** são separadas por vírgula (`uf=SP,RJ`). Espaços em volta de cada item são removidos;
   itens repetidos são ignorados; item vazio (`uf=SP,`) → 400.
4. **Parâmetro repetido** na URL (`uf=SP&uf=RJ`) → 400. Use a vírgula.
5. **Valor vazio** (`uf=`) → 400.
6. **Valor inválido em parâmetro de consulta → 400**, inclusive sigla, slug ou id inexistente
   (`uf=XX`, `indicador=inexistente`, `recorte=99999`). O **404** é só para recurso inexistente
   no **caminho** (`/estados/XX/`, `/indicadores/inexistente/`, `/registros/99999/`).
7. **Booleanos** aceitam só `true` e `false` (minúsculas). `1`, `0`, `True`, `sim` → 400.
8. **Anos** são inteiros de 4 dígitos dentro do intervalo de anos com registros (hoje 2012 a
   2025, lido do banco, nunca fixo no código). Fora dele → 400 com a mensagem
   `Ano fora do intervalo disponível (2012 a 2025).`
9. `ano` não convive com `ano_min`/`ano_max` (→ 400). `ano_min > ano_max` → 400.
10. Todos os erros de validação de uma requisição vêm juntos em `erros`, não só o primeiro.

---

## 3. Objetos compartilhados

Os mesmos objetos aparecem em `/registros/`, `/ranking/`, `/comparacao/` e `/populacao/`.

**Localidade**
```json
{"nivel": "uf", "codigo": "BA", "codigo_ibge": "29", "nome": "Bahia"}
```

**Indicador (resumo)**
```json
{"slug": "homicidio-doloso", "nome": "Homicídio doloso"}
```
A unidade não fica no indicador, e sim no registro: o mesmo indicador pode ter registros em
vítimas e em ocorrências (ADR 0004).

**Unidade** — campo `unidade` do registro: `vitimas` | `ocorrencias`. Um fato com duas vítimas
conta 2 em `vitimas` e 1 em `ocorrencias`. `homicidio-doloso`, `latrocinio` e
`lesao-corporal-seguida-de-morte` têm as duas; os demais só a sua `unidade_padrao`. Taxa, variação
e participação são sempre calculadas **dentro da mesma unidade**.

**Recorte** — `null` quando o registro é o total do indicador.
```json
{
  "id": 2,
  "rotulo": "Polícia Militar, em serviço",
  "itens": [
    {"dimensao": "corporacao", "valor": "Polícia Militar"},
    {"dimensao": "situacao_policial", "valor": "Em serviço"}
  ]
}
```
`itens` vem na ordem da `chave` do recorte (dimensões em ordem alfabética).

**Fonte (resumo)**
```json
{"id": 1, "nome": "Secretarias Estaduais de Segurança Pública e/ou Defesa Social (compilação FBSP)"}
```
O catálogo completo, com ids fixos, está na seção 4.5.

**Taxa** — sempre presente.
```json
{"valor": "40.94", "base": "100 mil habitantes", "origem": "calculada",
 "fonte": {"id": 2, "nome": "IBGE – Estimativas da população residente"}}
```
- `base`: `base_taxa` do indicador; `null` quando o indicador não tem base (hoje, nenhum indicador com registros).
- `origem`: `calculada` (valor ÷ população do IBGE × 100 000, quando a base é 100 mil habitantes
  e há população para o ano e a localidade) ou `publicada` (`taxa_publicada` arredondada). `null`
  quando `valor` é `null`, ou seja, sempre que não há taxa: sem valor do registro ou sem
  denominador (ADR 0008).
- `fonte`: fonte do **denominador**, lida de `INDICADORES.fonte_taxa` (ADR 0005), a mesma para
  `origem` `calculada` e `publicada`: IBGE – Estimativas para habitantes, IBGE – Projeções para
  mulheres, Senatran para veículos, Banco Central para instituições. `null` quando `valor` é
  `null`.
- `valor` é `null` quando: `situacao = nao_disponivel`; ou não há denominador
  (ex.: totais regionais de feminicídio, de roubo e furto de veículo e de roubo a instituição
  financeira).

**Variação** — sempre presente.
```json
{"ano_referencia": 2024, "valor_pct": "-3.10", "taxa_pct": "-3.60"}
```
- `ano_referencia` é sempre `ano - 1`.
- `valor_pct` = (valor − valor do ano anterior) ÷ valor do ano anterior × 100, mesma localidade,
  indicador, recorte e unidade. `taxa_pct` é o mesmo cálculo sobre a taxa **em precisão total**
  (arredonda-se só o resultado).
- `taxa_pct` corresponde à coluna "Variação (%)" das tabelas do FBSP, que é a variação da taxa, e
  não a do valor absoluto.
- Ficam `null` quando falta um dos anos, quando um dos valores é nulo ou quando a base é zero.

**Participação** — sempre presente. Substitui as proporções publicadas pelo FBSP (T09 e T21),
que não são importadas (ADR 0004).
```json
{"referencia": {"tipo": "indicador_pai", "indicador": "mvi"}, "valor_pct": "16.19"}
```
- Registro **sem recorte**, cujo indicador tem pai com registros: valor ÷ valor do pai × 100, na
  mesma localidade, ano e unidade, sem recorte (`tipo = indicador_pai`). Ex.: MDIP em relação às
  MVI (T09); feminicídio em relação aos homicídios de mulheres (T21); roubo de celular em relação
  ao roubo.
- Registro **com recorte**: valor ÷ valor do total do mesmo indicador × 100, na mesma
  localidade, ano e unidade (`tipo = total_do_indicador`, `indicador` = o próprio). Ex.: mortes
  por policiais militares em serviço em relação ao total de MDIP.
- `referencia: null` e `valor_pct: null` quando não há referência: indicador-raiz (`mvi`,
  `roubo`) sem recorte, ou pai agrupador sem registros (`furto-veiculo`, `furto-celular`).
- `valor_pct: null` (com `referencia` preenchida) quando o numerador ou o denominador é nulo, o
  denominador é zero ou o pai não tem registro nessa unidade (ex.: homicídio doloso em
  ocorrências, já que a MVI só existe em vítimas).
- **Não some participações**: os subtipos não fecham 100% (o total de roubo é menor que a soma
  dos subtipos; uma ocorrência pode estar em mais de um subtipo).
- Calculada no SQL por subconsulta, em precisão total, como a variação; arredondada só na
  serialização.

---

## 4. Recursos

Paginação só em `/registros/` e `/populacao/`. Os demais recursos devolvem a coleção inteira
(`pagination_class = None`).

- **Lista paginada:** objeto `{"count", "next", "previous", "results"}`. `next` e `previous` são
  URLs absolutas que preservam os demais parâmetros.
- **Catálogos** (`/regioes/`, `/estados/`, `/indicadores/`, `/recortes/`, `/fontes/`): **array
  JSON** na raiz, sem envelope.
- **Consultas agregadas** (`/ranking/`, `/comparacao/`, `/metadados/`): **objeto JSON**, com os
  parâmetros efetivamente usados ecoados (inclusive os valores padrão resolvidos).

Toda lista tem ordem determinística; quando a ordem pedida empata, desempata pela ordem padrão do
recurso e, por último, por `id`.

### 4.1 `/regioes/` e `/regioes/{sigla}/`

Parâmetros: nenhum além de `formato=json`. Ordem: canônica (BR, N, NE, SE, S, CO).

```json
[
  {"sigla": "BR", "nome": "Brasil", "tipo": "pais", "codigo_ibge": "1",
   "estados": ["AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS", "MT", "PA",
               "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO"]},
  {"sigla": "N", "nome": "Norte", "tipo": "regiao", "codigo_ibge": "1",
   "estados": ["AC", "AM", "AP", "PA", "RO", "RR", "TO"]}
]
```
- `estados`: siglas das UFs da região, por sigla. Para o Brasil, as 27 UFs.
- Detalhe: mesmo objeto. Sigla inexistente → 404.

### 4.2 `/estados/` e `/estados/{uf}/`

Parâmetros: `regiao` (lista de siglas de região; `BR` → 400). Ordem: por sigla.

```json
[{"sigla": "BA", "nome": "Bahia", "codigo_ibge": "29",
  "regiao": {"sigla": "NE", "nome": "Nordeste"}}]
```

### 4.3 `/indicadores/` e `/indicadores/{slug}/`

Parâmetros: nenhum além de `formato=json`. Ordem: `ordem` do indicador (pré-ordem da hierarquia,
seção 4.3.1). Lista **plana**; a árvore aninhada está em `/metadados/`.

```json
[
  {"slug": "feminicidio", "nome": "Feminicídio", "descricao": "…",
   "unidade_padrao": "vitimas", "unidades": ["vitimas"], "base_taxa": "100 mil mulheres",
   "fonte_taxa": {"id": 3, "nome": "IBGE – Projeções da população"},
   "indicador_pai": "homicidio-mulheres", "subtipos": [],
   "possui_registros": true, "anos": [2024, 2025],
   "recortes": []}
]
```
- `unidade_padrao`: `vitimas` | `ocorrencias`, a unidade usada quando o cliente não pede outra.
- `unidades`: unidades com registros do indicador, na ordem `vitimas`, `ocorrencias`
  (`["vitimas", "ocorrencias"]` em homicídio doloso, latrocínio e lesão corporal seguida de
  morte; `[]` em agrupadores).
- `base_taxa`: texto de `INDICADORES.base_taxa`, ou `null`.
- `fonte_taxa`: fonte do denominador da taxa (`{"id", "nome"}`), ou `null` quando `base_taxa` é
  `null` (ADR 0005).
- `indicador_pai`: slug ou `null`. `subtipos`: slugs dos **filhos diretos**, na ordem.
- `possui_registros`: `false` para agrupadores sem dado próprio (hoje só `furto`).
- `anos`: anos com registros do indicador (em qualquer unidade), crescentes. `[]` em agrupadores.
- `recortes`: `[{"id", "rotulo"}]` dos recortes com registros desse indicador, por `chave`.

#### 4.3.1 Hierarquia

A hierarquia significa **"está contido em"**, nunca **"é a soma de"**: os filhos de um indicador
não somam o pai (uma ocorrência pode estar em mais de um subtipo de roubo; o total de roubo é
menor que a soma dos subtipos), e o cliente não deve somá-los.

| `ordem` | Slug | Pai |
| ---: | :--- | :--- |
| 1 | `mvi` | — |
| 2 | `homicidio-doloso` | `mvi` |
| 3 | `homicidio-mulheres` | `homicidio-doloso` |
| 4 | `feminicidio` | `homicidio-mulheres` |
| 5 | `latrocinio` | `mvi` |
| 6 | `lesao-corporal-seguida-de-morte` | `mvi` |
| 7 | `morte-intervencao-policial` | `mvi` |
| 8 | `roubo` | — |
| 9 | `roubo-veiculo` | `roubo` |
| 10 | `roubo-celular` | `roubo` |
| 11 | `roubo-transeunte` | `roubo` |
| 12 | `roubo-residencia` | `roubo` |
| 13 | `roubo-estabelecimento-comercial` | `roubo` |
| 14 | `roubo-instituicao-financeira` | `roubo` |
| 15 | `roubo-carga` | `roubo` |
| 16 | `furto` | — (agrupador, sem registros) |
| 17 | `furto-veiculo` | `furto` |
| 18 | `furto-celular` | `furto` |

Feminicídio é filho de **homicídio de mulheres**, que é filho de homicídio doloso: a T03 define
homicídio doloso como "incluindo feminicídios", e a T21 publica feminicídio como parte dos
homicídios de mulheres ("proporção de feminicídios em relação aos homicídios de mulheres").
`INDICADORES.ordem` (inteiro único) é preenchido por `catalogo/referencia.py`.

### 4.4 `/recortes/`

Parâmetros: `indicador` (lista de slugs). Ordem: por `chave`.

```json
[
  {"id": 2, "rotulo": "Polícia Militar, em serviço",
   "chave": "corporacao=Polícia Militar;situacao_policial=Em serviço",
   "itens": [{"dimensao": "corporacao", "valor": "Polícia Militar"},
             {"dimensao": "situacao_policial", "valor": "Em serviço"}],
   "indicadores": ["morte-intervencao-policial"]}
]
```
- `indicadores`: slugs dos indicadores que têm registros com esse recorte.
- O `id` é o que se passa em `recorte=` nos outros recursos. A importação cria os recortes sempre
  na mesma ordem (a de `mapeamento.py`), de modo que um banco limpo reproduz os mesmos `id`s; há
  teste para isso.

### 4.5 `/fontes/`

Parâmetros: nenhum além de `formato=json`. Ordem: `id`.

```json
[{"id": 2, "slug": "ibge-estimativas", "nome": "IBGE – Estimativas da população residente",
  "descricao": "Estimativas da população residente no Brasil e nas Unidades da Federação, com data de referência em 1º de julho de 2024 e de 2025.",
  "url": "https://www.ibge.gov.br/estatisticas/sociais/populacao/9103-estimativas-de-populacao.html"}]
```

Catálogo fixo, criado nesta ordem por `catalogo/referencia.py` com `update_or_create(slug=…)`,
de modo que um banco limpo reproduz os mesmos `id`s (há teste). Fonte nova entra no fim; nenhuma é
reordenada nem removida. Descrições e URLs completas no ADR 0005.

| `id` | `slug` | `nome` | Onde aparece |
| ---: | :--- | :--- | :--- |
| 1 | `secretarias-seguranca` | Secretarias Estaduais de Segurança Pública e/ou Defesa Social (compilação FBSP) | `fonte` de todo registro |
| 2 | `ibge-estimativas` | IBGE – Estimativas da população residente | `fonte` da população; `taxa.fonte` na base 100 mil habitantes |
| 3 | `ibge-projecoes` | IBGE – Projeções da população | `taxa.fonte` na base 100 mil mulheres |
| 4 | `senatran-frota` | Senatran – Frota de veículos | `taxa.fonte` na base 100 mil veículos |
| 5 | `bcb-instituicoes` | Banco Central do Brasil – Instituições financeiras | `taxa.fonte` na base 100 instituições |

### 4.6 `/populacao/`

Paginado. Parâmetros: `nivel`, `uf`, `regiao`, `ano`, `ano_min`, `ano_max`, `ordenar`, mais os
reservados. `nivel`, `uf` e `regiao` seguem exatamente a regra da seção 4.7.2.

`ordenar` aceita `ano`, `localidade`, `valor`. Ordem padrão: `localidade` (canônica), `ano`.

Sem `nivel`, `uf` nem `regiao`, a resposta traz só as UFs: 54 linhas (27 UFs × 2 anos). As 66
linhas (33 localidades × 2 anos) exigem a lista explícita, como no exemplo:

`GET /api/v1/populacao/?nivel=pais,regiao,uf`
```json
{
  "count": 66, "next": null, "previous": null,
  "results": [
    {"id": 1, "ano": 2024,
     "localidade": {"nivel": "pais", "codigo": "BR", "codigo_ibge": "1", "nome": "Brasil"},
     "valor": "212583750",
     "fonte": {"id": 2, "nome": "IBGE – Estimativas da população residente"}}
  ]
}
```

### 4.7 `/registros/` e `/registros/{id}/`

Paginado. O detalhe devolve o mesmo objeto de um item de `results`; id inexistente → 404.

#### 4.7.1 Parâmetros

| Parâmetro | Valores | Padrão | Regra |
| :--- | :--- | :--- | :--- |
| `nivel` | lista de `pais`, `regiao`, `uf` | `uf` (ver 4.7.2) | Tipo de localidade. |
| `uf` | lista de siglas de UF | — | Implica `nivel=uf`. |
| `regiao` | lista de `N`, `NE`, `SE`, `S`, `CO` | — | Exige `nivel` explícito. `BR` → 400. |
| `indicador` | lista de slugs | todos | Slug inexistente → 400. |
| `incluir_subtipos` | `true`, `false` | `false` | Exige `indicador`. Inclui **todos os descendentes**, em qualquer profundidade (`homicidio-doloso` traz também `homicidio-mulheres` e `feminicidio`). |
| `ano` | lista de anos | todos | Não convive com `ano_min`/`ano_max`. |
| `ano_min`, `ano_max` | ano | — | Intervalo fechado; podem vir sozinhos. |
| `unidade` | `padrao`, `todas` ou lista de `vitimas`, `ocorrencias` | `padrao` | `padrao`: a `unidade_padrao` de cada indicador. `todas`: as duas. Lista: só essas. `padrao`/`todas` não se misturam com a lista. Se `indicador` foi informado e nenhum deles tem registros na unidade pedida → 400 (`O indicador mvi não tem registros em ocorrencias.`). |
| `recorte` | `total`, `todos` ou lista de ids | `total` | `total`: só registros sem recorte. `todos`: totais e recortes. Ids: só esses recortes (sem o total). `todos`/`total` não se misturam com ids. |
| `situacao` | lista de `informado`, `inexistente`, `nao_disponivel` | todas | — |
| `ordenar` | lista de campos (4.7.3) | ordem padrão | Prefixo `-` inverte. |

`unidade=padrao` segue a mesma lógica de `recorte=total`: sem pedido explícito, nunca se
misturam vítimas e ocorrências do mesmo crime, o que levaria a somas sem sentido no cliente.

Agrupador sem registros em `indicador` (hoje `furto`) **sem** `incluir_subtipos=true` → 400
(`O indicador furto não tem registros próprios; use incluir_subtipos=true.`). Isso impede que a
ausência de total de furtos pareça um "zero".

#### 4.7.2 Regra de `nivel`, `uf` e `regiao`

Misturar Brasil, regiões e UFs na mesma resposta é o mesmo risco de dupla contagem que motivou
`recorte=total`: uma soma no cliente contaria as mesmas vítimas três vezes. Por isso, **sem
`nivel` explícito, a resposta tem um único nível**, e a mistura só acontece quando pedida por lista.

| Requisição | Resultado |
| :--- | :--- |
| nenhum de `nivel`, `uf`, `regiao` | `nivel=uf`: as 27 UFs |
| `uf=SP,RJ` | essas UFs (`nivel=uf` implícito) |
| `nivel=uf&uf=SP` | SP |
| `nivel=uf&regiao=NE` | as 9 UFs do Nordeste |
| `nivel=regiao` | as 5 regiões |
| `nivel=regiao&regiao=NE,SE` | os agregados do Nordeste e do Sudeste |
| `nivel=pais` | o Brasil |
| `nivel=pais,regiao,uf` | todas as 33 localidades (mistura pedida explicitamente) |
| `regiao=NE` sem `nivel` | **400**: ambíguo (UFs do Nordeste ou agregado?); informe `nivel` |
| `uf` e `regiao` juntos | **400**: são mutuamente exclusivos |
| `uf` com `nivel` diferente de `uf` (ex.: `nivel=regiao&uf=SP`) | **400** |
| `regiao` com `nivel=pais` | **400** |
| `uf` ou `regiao` com mais de um nível em `nivel` | **400**: filtre localidades com um nível só; para UF × região × Brasil use `/comparacao/` |

#### 4.7.3 Ordenação

| Nome em `ordenar` | Campo da resposta | Observação |
| :--- | :--- | :--- |
| `ano` | `ano` | |
| `indicador` | `indicador` | Pela `ordem` do indicador, não alfabética. |
| `localidade` | `localidade` | Ordem canônica (1.1). |
| `recorte` | `recorte` | Total primeiro, depois por `chave`. |
| `unidade` | `unidade` | `vitimas` antes de `ocorrencias`. |
| `valor` | `valor` | |
| `taxa` | `taxa.valor` | Taxa arredondada a 2 casas (1.2). |
| `variacao_valor` | `variacao.valor_pct` | Arredondada a 2 casas. |
| `variacao_taxa` | `variacao.taxa_pct` | Arredondada a 2 casas. |
| `participacao` | `participacao.valor_pct` | Arredondada a 2 casas. |

- **Ordem padrão:** `indicador`, `localidade`, `recorte`, `unidade`, `ano`.
- O critério pedido vem primeiro; a ordem padrão completa o desempate, e `id` fecha. Assim a
  paginação é estável.
- **Nulos sempre ao final**, nas duas direções (`ordenar=taxa` e `ordenar=-taxa`).
- Campo fora da tabela → 400. Campo repetido (`ordenar=ano,-ano`) → 400.
- Taxa, variação e participação são **anotadas no SQL** (`queries.py`), e a ordenação e a paginação acontecem no
  banco. Nunca ordenar em Python uma lista paginada.

#### 4.7.4 Formato do registro

```json
{
  "id": 18342,
  "ano": 2025,
  "localidade": {"nivel": "uf", "codigo": "BA", "codigo_ibge": "29", "nome": "Bahia"},
  "indicador": {"slug": "mvi", "nome": "Mortes Violentas Intencionais"},
  "recorte": null,
  "unidade": "vitimas",
  "valor": "5800",
  "situacao": "informado",
  "metodo": "publicado",
  "taxa": {"valor": "40.94", "base": "100 mil habitantes", "origem": "calculada",
           "fonte": {"id": 2, "nome": "IBGE – Estimativas da população residente"}},
  "taxa_publicada": "40.9415826",
  "variacao": {"ano_referencia": 2024, "valor_pct": "-3.10", "taxa_pct": "-3.60"},
  "participacao": {"referencia": null, "valor_pct": null},
  "fonte": {"id": 1, "nome": "Secretarias Estaduais de Segurança Pública e/ou Defesa Social (compilação FBSP)"},
  "observacao": null
}
```
Valores ilustrativos. Regras dos campos: as do Roteiro (seção "Formato dos registros") e a
seção 3 deste documento. Em `situacao = nao_disponivel`, `valor`, `taxa.valor` e as variações são
nulos; em `inexistente`, `valor` é `"0"`. Em `metodo = soma_ufs`, `taxa_publicada` é nula.

### 4.8 `/ranking/`

As 27 UFs ordenadas por um indicador em um ano. Sem paginação. Brasil e regiões não entram.

| Parâmetro | Obrigatório | Padrão | Regra |
| :--- | :--- | :--- | :--- |
| `indicador` | sim | — | **Um** slug. Agrupador (`furto`) → 400. |
| `ano` | não | último ano com registros do indicador (hoje 2025) | **Um** ano. Ano sem registros do indicador → 400. |
| `criterio` | não | `taxa` | `taxa`, `valor` ou `participacao`. |
| `unidade` | não | `unidade_padrao` do indicador | **Uma**: `vitimas` ou `ocorrencias`. Unidade sem registros do indicador → 400. |
| `recorte` | não | `total` | `total` ou **um** id de recorte. `todos` ou lista → 400. |

Não aceita `uf`, `regiao`, `nivel` nem `ordenar` (→ 400). Filtrar o ranking por região fica para
uma versão futura, como parâmetro opcional.

- Posição em ordem **decrescente** do critério (1 = maior valor ou taxa), sobre o valor já
  arredondado (1.2). Empates têm a mesma posição e a seguinte salta (1, 2, 2, 4), como em
  `posicoes_com_empate`.
- UF com o critério nulo (`nao_disponivel`, ou taxa sem denominador) vem ao final, com
  `posicao: null`, em ordem de sigla. `inexistente` (valor 0) entra na classificação.
- Empate em posição: desempata por sigla.
- `criterio=taxa` em indicador sem base de taxa → 400. `criterio=participacao` sem referência
  (indicador-raiz sem recorte, ou filho de agrupador) → 400.

```json
{
  "indicador": {"slug": "mvi", "nome": "Mortes Violentas Intencionais",
                "base_taxa": "100 mil habitantes"},
  "ano": 2025,
  "criterio": "taxa",
  "unidade": "vitimas",
  "recorte": null,
  "results": [
    {"posicao": 1,
     "localidade": {"nivel": "uf", "codigo": "AP", "codigo_ibge": "16", "nome": "Amapá"},
     "valor": "…", "situacao": "informado", "metodo": "publicado",
     "taxa": {"valor": "…", "base": "100 mil habitantes", "origem": "calculada", "fonte": {"id": 2, "nome": "…"}},
     "variacao": {"ano_referencia": 2024, "valor_pct": "…", "taxa_pct": "…"},
     "participacao": {"referencia": null, "valor_pct": null},
     "fonte": {"id": 1, "nome": "…"},
     "observacao": null}
  ]
}
```
`results` tem sempre 27 itens. Exemplo com participação: `indicador=morte-intervencao-policial&
criterio=participacao` classifica as UFs pela parcela das MVI causada por intervenção policial
(o mesmo da T09).

### 4.9 `/comparacao/`

Série de uma UF ao lado da sua região e do Brasil (RF13). Sem paginação.

| Parâmetro | Obrigatório | Padrão | Regra |
| :--- | :--- | :--- | :--- |
| `uf` | sim | — | **Uma** sigla de UF. A região é a da UF. |
| `indicador` | sim | — | **Um** slug. Agrupador → 400. |
| `ano_min`, `ano_max` | não | primeiro e último ano com registros do indicador | Intervalo fechado. Sem registros no intervalo → 400. |
| `unidade` | não | `unidade_padrao` do indicador | **Uma**: `vitimas` ou `ocorrencias`. Unidade sem registros do indicador → 400. |
| `recorte` | não | `total` | `total` ou **um** id. |

Não aceita `ano` (use `ano_min` = `ano_max`), `nivel`, `regiao` nem `ordenar`.

```json
{
  "indicador": {"slug": "feminicidio", "nome": "Feminicídio",
                "base_taxa": "100 mil mulheres"},
  "unidade": "vitimas",
  "recorte": null,
  "ano_min": 2024,
  "ano_max": 2025,
  "series": [
    {"localidade": {"nivel": "uf", "codigo": "BA", "codigo_ibge": "29", "nome": "Bahia"},
     "pontos": [
       {"ano": 2024, "valor": "…", "situacao": "informado", "metodo": "publicado",
        "taxa": {…}, "variacao": {…}, "participacao": {…}, "fonte": {…}, "observacao": null},
       {"ano": 2025, "…": "…"}
     ]},
    {"localidade": {"nivel": "regiao", "codigo": "NE", "codigo_ibge": "2", "nome": "Nordeste"},
     "pontos": [{"ano": 2024, "metodo": "soma_ufs", "taxa": {"valor": null, "…": "…"}, "…": "…"}]},
    {"localidade": {"nivel": "pais", "codigo": "BR", "codigo_ibge": "1", "nome": "Brasil"},
     "pontos": ["…"]}
  ]
}
```
- `series` tem sempre 3 itens, nesta ordem: UF, região, Brasil.
- `pontos` em ordem crescente de ano, com os **mesmos anos** nas três séries (a importação garante
  as 33 localidades em todos os anos de cada indicador; há teste).
- Cada ponto tem os mesmos campos de um registro, menos `id`, `localidade`, `indicador`,
  `recorte` e `unidade`, que já estão no nível de cima, e menos `taxa_publicada`, que fica só em
  `/registros/`, como nos itens de `/ranking/` e nas colunas do CSV (5.3).

### 4.10 `/metadados/`

Objeto único para o dashboard montar filtros e legendas com uma requisição (RF09). Sem parâmetros
além de `formato=json`.

```json
{
  "carga": {
    "versao": "…", "concluida_em": "2026-10-27T15:04:05-03:00", "total_registros": 1980,
    "arquivos": [{"nome": "anuario-2026.xlsx", "sha256": "6b01f4ed…"}]
  },
  "anos": {"min": 2012, "max": 2025},
  "niveis": ["pais", "regiao", "uf"],
  "unidades": [
    {"codigo": "vitimas", "nome": "Número de vítimas"},
    {"codigo": "ocorrencias", "nome": "Número de ocorrências"}
  ],
  "situacoes": [
    {"codigo": "informado", "nome": "Informado"},
    {"codigo": "inexistente", "nome": "Fenômeno inexistente"},
    {"codigo": "nao_disponivel", "nome": "Informação não disponível"}
  ],
  "metodos": [
    {"codigo": "publicado", "nome": "Publicado pelo FBSP"},
    {"codigo": "soma_ufs", "nome": "Calculado pelo projeto como soma das UFs"}
  ],
  "fontes": [{"id": 1, "slug": "secretarias-seguranca", "nome": "…"}, "…"],
  "indicadores": [
    {"slug": "mvi", "nome": "…", "descricao": "…", "unidade_padrao": "vitimas",
     "unidades": ["vitimas"], "base_taxa": "100 mil habitantes",
     "fonte_taxa": {"id": 2, "nome": "IBGE – Estimativas da população residente"},
     "indicador_pai": null,
     "subtipos": [
       {"slug": "homicidio-doloso", "indicador_pai": "mvi", "…": "…",
        "subtipos": [{"slug": "homicidio-mulheres", "…": "…",
                      "subtipos": [{"slug": "feminicidio", "…": "…", "subtipos": []}]}]}
     ],
     "possui_registros": true, "anos": [2012, 2013, "…", 2025], "recortes": []}
  ]
}
```
- `indicadores` é a **árvore aninhada** (raízes por `ordem`). Cada nó tem os mesmos campos, na
  mesma ordem, de um item de `/indicadores/` (4.3), inclusive `descricao` e `indicador_pai`; a
  única diferença é que `subtipos` traz os objetos dos filhos, e não os slugs.
- `carga` vem da carga atual: a `Carga` com status concluído e o maior `concluida_em`. `versao` é
  a mesma usada no ETag. Sem nenhuma carga concluída, `/metadados/` responde 503 como os demais
  recursos (seção 7.1); `carga` nunca é `null`.
- `fontes`: o catálogo inteiro (seção 4.5), com `id`, `slug` e `nome`.

---

## 5. Exportação em CSV

### 5.1 Onde e como

- **Recursos com CSV:** `/registros/`, `/populacao/`, `/ranking/`, `/comparacao/`. Os demais
  (catálogos, `/metadados/`, detalhes `/{id}/`) respondem **406** a `formato=csv` ou
  `Accept: text/csv`.
- **Negociação:** `formato` tem precedência sobre `Accept`. Sem os dois, ou com `Accept: */*`,
  JSON. Configure `REST_FRAMEWORK["URL_FORMAT_OVERRIDE"] = "formato"` e troque o 404 que o DRF
  devolve para formato desconhecido por 406.
- **Filtros, validação e ordenação:** os mesmos da versão JSON. Um parâmetro inválido devolve o
  erro em Problem Details (JSON), **nunca** em CSV.
- **Sem paginação:** a exportação traz o recorte completo; `pagina`/`tamanho` → 400.
- **Limite:** 50 000 linhas de dados. A contagem é feita antes de começar o streaming; acima do
  limite → 400 com `erros: [{"parametro": "formato", "mensagem": "A exportação teria N linhas; o
  limite é 50000. Restrinja com ano, uf ou indicador."}]`.
- **Streaming:** `StreamingHttpResponse` com `queryset.iterator(chunk_size=2000)`; os cabeçalhos de
  cache (seção 7) também valem.

### 5.2 Dialeto

- RFC 4180: separador `,`, aspas `"` só quando necessário, linhas terminadas em `\r\n`.
- UTF-8 **sem BOM** (a API é para reuso por programas; o BOM corrompe o nome da primeira coluna em
  vários leitores).
- Decimal com ponto, nos mesmos formatos e arredondamentos do JSON (1.2). Nulo = campo vazio.
- Primeira linha = cabeçalho, sempre presente, mesmo sem dados. **Nenhuma linha de comentário.**
- `Content-Type: text/csv; charset=utf-8; header=present`
- `Content-Disposition: attachment; filename="anuario-<recurso>.csv"` (ex.: `anuario-registros.csv`).

### 5.3 Achatamento

Objetos aninhados viram colunas com o caminho unido por `_` (`taxa.valor` → `taxa_valor`).
Exceções: `fonte` e `taxa.fonte` viram só o **nome** (`fonte`, `taxa_fonte`); `recorte` vira
`recorte_id` e `recorte_rotulo` (os itens não entram); o indicador vira `indicador_slug` e
`indicador_nome`; `participacao.referencia` vira `participacao_tipo` e `participacao_indicador`.
A ordem das colunas abaixo é contrato.

**`/registros/`** — uma linha por registro, na mesma ordem da versão JSON.
```
id,ano,localidade_nivel,localidade_codigo,localidade_codigo_ibge,localidade_nome,indicador_slug,indicador_nome,recorte_id,recorte_rotulo,unidade,valor,situacao,metodo,taxa_valor,taxa_base,taxa_origem,taxa_fonte,taxa_publicada,variacao_ano_referencia,variacao_valor_pct,variacao_taxa_pct,participacao_tipo,participacao_indicador,participacao_valor_pct,fonte,observacao
```

**`/populacao/`**
```
id,ano,localidade_nivel,localidade_codigo,localidade_codigo_ibge,localidade_nome,valor,fonte
```

**`/ranking/`** — uma linha por UF; o contexto da consulta se repete em cada linha, porque o CSV
não tem onde guardá-lo.
```
ano,indicador_slug,indicador_nome,unidade,criterio,recorte_id,recorte_rotulo,posicao,localidade_nivel,localidade_codigo,localidade_codigo_ibge,localidade_nome,valor,situacao,metodo,taxa_valor,taxa_base,taxa_origem,taxa_fonte,variacao_ano_referencia,variacao_valor_pct,variacao_taxa_pct,participacao_tipo,participacao_indicador,participacao_valor_pct,fonte,observacao
```

**`/comparacao/`** — formato longo: uma linha por (série, ano), séries na ordem UF, região, Brasil.
```
indicador_slug,indicador_nome,unidade,recorte_id,recorte_rotulo,localidade_nivel,localidade_codigo,localidade_codigo_ibge,localidade_nome,ano,valor,situacao,metodo,taxa_valor,taxa_base,taxa_origem,taxa_fonte,variacao_ano_referencia,variacao_valor_pct,variacao_taxa_pct,participacao_tipo,participacao_indicador,participacao_valor_pct,fonte,observacao
```

`fonte`, `taxa_fonte` e `situacao` estão em todas as linhas (RF11, RNF12).

---

## 6. Erros

Problem Details (RFC 9457), `application/problem+json`, já implementado em `apps/api/erros.py`.
Erros de validação trazem `erros: [{"parametro", "mensagem"}]`; `parametro` é o nome do parâmetro
de consulta (vazio quando o erro é da combinação, como `uf` + `regiao`, e então a mensagem cita os
dois).

| Status | Quando |
| :--- | :--- |
| 400 | Parâmetro desconhecido, repetido, vazio ou inválido (inclusive sigla, slug ou id inexistente em parâmetro de consulta); combinação proibida (4.7.2); `pagina`/`tamanho` inválidos, além da última página ou acima de 1000; `pagina`/`tamanho` com CSV ou em recurso sem paginação; exportação acima de 50 000 linhas. |
| 404 | Recurso inexistente no **caminho**: `/estados/XX/`, `/regioes/XX/`, `/indicadores/xx/`, `/registros/99999/`, ou rota inexistente. |
| 405 | `POST`, `PUT`, `PATCH`, `DELETE`. |
| 406 | `formato` diferente de `json`/`csv`; CSV pedido em recurso sem CSV; `Accept` sem nenhum tipo suportado. |
| 429 | Limite de requisições, se a limitação para anônimos for ativada. |
| 500 | Erro interno, corpo genérico, sem detalhes técnicos. |
| 503 | Nenhuma carga de dados concluída (seção 7.1). |

Note que `tamanho` acima de 1000 é **400**, e não o corte silencioso que o DRF faz por padrão.

---

## 7. Cache

- `Cache-Control: public, max-age=86400` em toda resposta 200 (JSON e CSV).
- `ETag: W/"<versao da carga>-<json|csv>"`: muda com uma nova importação e difere entre as
  representações da mesma URL.
- `Vary: Accept`, porque a mesma URL tem duas representações.
- `If-None-Match` com o ETag atual → 304 sem corpo.
- Erros (4xx e 5xx) não levam `Cache-Control: public`.

### 7.1 Sem carga concluída

A versão do ETag é a da carga atual: a `Carga` com status concluído e o maior `concluida_em`.
Cargas em andamento ou que falharam são ignoradas; como a importação roda em uma transação, a carga
anterior continua valendo até a nova ser concluída (ADR 0005).

Se não existe nenhuma carga concluída, **todo recurso de `/api/v1/`** responde **503** em Problem
Details, com `Cache-Control: no-store` e sem `ETag`:

```json
{"type": "about:blank", "title": "Serviço indisponível", "status": 503,
 "detail": "Nenhuma carga de dados foi concluída. Tente novamente mais tarde."}
```

- A verificação vem depois do 405 (método) e do 406 (formato) e antes da validação dos parâmetros.
- `/api/v1/schema/`, `/api/v1/docs/` e `/api/v1/redoc/` não dependem dos dados e continuam com 200.
- Motivo: listas vazias com 200 ficariam 24 h em cache em clientes e intermediários, e não haveria
  intervalo de anos para validar `ano` (seção 2, regra 8).

---

## 8. Testes de contrato obrigatórios

Cada item vira ao menos um teste em `backend/tests/api/` (os de cálculo também em
`tests/registros/`). Todos estão implementados; entre parênteses, onde.

- [x] Parâmetro desconhecido, repetido e vazio → 400 em todos os recursos, com o nome em `erros`
      (`test_regras_comuns.py`, `test_catalogos.py`, `test_parametros.py`).
- [x] `formato=json` aceito em todos; `formato=csv` → 406 nos recursos sem CSV; `formato=xml` → 406
      (`test_regras_comuns.py`, `test_catalogos.py`, `test_csv.py`).
- [x] `pagina`/`tamanho` → 400 em recursos sem paginação e com CSV; `tamanho=1001` → 400
      (`test_catalogos.py`, `test_csv.py`, `test_registros.py`).
- [x] Cada linha da tabela 4.7.2 (nível, UF e região), um teste por linha (`test_registros.py`).
- [x] `recorte` padrão `total` não traz recortes; `todos` traz; id inexistente → 400
      (`test_registros.py`).
- [x] `incluir_subtipos=true` em `homicidio-doloso` traz `homicidio-mulheres` e `feminicidio`
      (`test_registros.py`).
- [x] `indicador=furto` sem `incluir_subtipos` → 400; com ele, só `furto-veiculo` e `furto-celular`
      (`test_registros.py`).
- [x] `unidade` padrão: `homicidio-doloso` sai só em vítimas; `unidade=todas` traz vítimas e
      ocorrências; `indicador=mvi&unidade=ocorrencias` → 400; ranking e comparação ecoam a
      unidade resolvida (`test_registros.py`, `test_ranking_comparacao.py`).
- [x] Participação: MDIP total ÷ MVI e feminicídio ÷ homicídio de mulheres batem com a T09 e a T21
      (até 1e-6, antes de arredondar); recorte da T08 ÷ total de MDIP; `mvi` e `furto-*` com
      `referencia: null`; homicídio doloso em ocorrências com `valor_pct: null`
      (`tests/registros/test_anotacoes.py`, `test_registros.py`).
- [x] Formatos decimais da tabela 1.2, inclusive arredondamento meio para longe do zero (`x.xx5`)
      e ausência de `-0.00` (`test_campos.py`, `test_registros.py`).
- [x] `ordenar=taxa` e `ordenar=-taxa` com nulos ao final; paginação sem itens repetidos nem
      perdidos ao percorrer todas as páginas com ordenação por campo com empates
      (`test_registros.py`, `tests/registros/test_anotacoes.py`).
- [x] Ranking: 27 itens, empates (1, 2, 2, 4) pelo valor arredondado, nulos ao final com
      `posicao: null`, `ano` padrão resolvido e ecoado (`test_ranking_comparacao.py`).
- [x] Comparação: 3 séries na ordem UF, região, Brasil, com os mesmos anos; região `soma_ufs`
      sem taxa nas bases sem denominador (`test_ranking_comparacao.py`).
- [x] CSV: cabeçalho exato de cada recurso (comparar a string), sem BOM, `\r\n`, campo vazio para
      nulo, erro de validação em JSON, limite de linhas (com o limite reduzido no teste)
      (`test_csv.py`).
- [x] Cache: `ETag` diferente para JSON e CSV, `Vary: Accept`, 304 com `If-None-Match`
      (`test_cache.py`).
- [x] Sem carga concluída: 503 em todos os recursos, com `Cache-Control: no-store` e sem `ETag`;
      `schema`, `docs` e `redoc` com 200. Carga em andamento ou com falha não muda o ETag vigente
      (`test_catalogos.py`, `test_cache.py`).
- [x] Fontes: banco limpo cria os ids 1 a 5 na ordem da seção 4.5; `taxa.fonte` de cada base de
      taxa é a fonte da tabela do ADR 0005; `taxa.fonte` nula quando `taxa.valor` é nulo
      (`tests/importacao/test_processo.py`, `test_regras_comuns.py`).
- [x] Nenhuma consulta N+1 (`django_assert_max_num_queries`) em listas, ranking e comparação
      (`test_catalogos.py`, `test_registros.py`, `test_ranking_comparacao.py`, `test_csv.py`,
      `test_metadados.py`, `tests/desempenho/test_p95.py`).
