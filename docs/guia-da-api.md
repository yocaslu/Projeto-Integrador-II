# Guia da API

Receitas para consultar os dados pela API REST. A especificação completa, com todas as regras de
validação e todas as colunas de CSV, está em [contrato-api.md](contrato-api.md); a documentação
interativa (Swagger UI), em `/api/v1/docs/`.

Os exemplos usam o ambiente local (`http://localhost:8000`) e os dados da carga atual; troque o
endereço pelo do servidor em que a aplicação estiver publicada.

## 1. O básico

- **Somente leitura.** Só `GET`, `HEAD` e `OPTIONS`; qualquer outro método responde 405. Não é
  preciso autenticação.
- **Prefixo** `/api/v1/`. Uma mudança incompatível criaria `/api/v2/`, sem tirar a v1 do ar.
- **Nomes em português.** UFs e regiões pela sigla (`BA`, `NE`), sem diferença entre maiúsculas e
  minúsculas; indicadores pelo slug (`mvi`, `feminicidio`, `roubo-veiculo`). Listas são separadas
  por vírgula: `uf=SP,RJ`.
- **Números como texto.** `"5473"`, `"36.80"`. Isso preserva a precisão do banco; converta para
  número no seu programa. Valores absolutos são inteiros; taxas e variações têm duas casas.
- **Parâmetro errado é erro.** Um parâmetro desconhecido, repetido, vazio ou com valor inexistente
  responde 400 explicando o problema, em vez de ser ignorado.

| Recurso | Para quê |
| --- | --- |
| `/metadados/` | Tudo de uma vez: anos, indicadores em árvore (com anos, unidades e recortes de cada um), fontes e a versão da carga. Comece por aqui. |
| `/indicadores/`, `/indicadores/{slug}/` | Catálogo dos 18 indicadores. |
| `/estados/`, `/estados/{uf}/`, `/regioes/`, `/regioes/{sigla}/` | As 27 UFs, as 5 regiões e o Brasil, com os códigos do IBGE. |
| `/recortes/` | Os 4 recortes de corporação e situação do policial. |
| `/fontes/` | As 5 fontes dos dados. |
| `/registros/`, `/registros/{id}/` | Os dados: valor, taxa, variação, participação, situação e notas. |
| `/ranking/` | As 27 UFs ordenadas por um critério. |
| `/comparacao/` | A série de uma UF ao lado da sua região e do Brasil. |
| `/populacao/` | A população do IBGE usada nas taxas (2012 a 2025). |

## 2. Indicadores disponíveis

| Slug | Indicador | Anos | Unidade padrão | Base da taxa |
| --- | --- | --- | --- | --- |
| `mvi` | Mortes Violentas Intencionais | 2012–2025 | vítimas | 100 mil habitantes |
| `homicidio-doloso` | Homicídio doloso | 2022–2025 | vítimas (também ocorrências) | 100 mil habitantes |
| `homicidio-mulheres` | Homicídio de mulheres | 2022–2025 | vítimas | 100 mil mulheres |
| `feminicidio` | Feminicídio | 2022–2025 | vítimas | 100 mil mulheres |
| `latrocinio` | Latrocínio | 2022–2025 | vítimas (também ocorrências) | 100 mil habitantes |
| `lesao-corporal-seguida-de-morte` | Lesão corporal seguida de morte | 2022–2025 | vítimas (também ocorrências) | 100 mil habitantes |
| `morte-intervencao-policial` | Morte decorrente de intervenção policial | 2022–2025 | vítimas | 100 mil habitantes |
| `roubo` | Roubo (total) | 2022–2025 | ocorrências | 100 mil habitantes |
| `roubo-veiculo` | Roubo de veículo | 2022–2025 | ocorrências | 100 mil veículos |
| `roubo-celular` | Roubo de celular | 2022–2025 | ocorrências | 100 mil habitantes |
| `roubo-transeunte` | Roubo a transeunte | 2022–2025 | ocorrências | 100 mil habitantes |
| `roubo-residencia` | Roubo a residência | 2022–2025 | ocorrências | 100 mil habitantes |
| `roubo-estabelecimento-comercial` | Roubo a estabelecimento comercial | 2022–2025 | ocorrências | 100 mil habitantes |
| `roubo-instituicao-financeira` | Roubo a instituição financeira | 2022–2025 | ocorrências | 100 instituições |
| `roubo-carga` | Roubo de carga | 2022–2025 | ocorrências | 100 mil habitantes |
| `furto` | Furto (só agrupa os subtipos; **não tem dados próprios**) | — | — | — |
| `furto-veiculo` | Furto de veículo | 2022–2025 | ocorrências | 100 mil veículos |
| `furto-celular` | Furto de celular | 2022–2025 | ocorrências | 100 mil habitantes |

A lista acima reflete a carga atual; `/metadados/` sempre traz a versão em vigor.

## 3. Receitas

### Um número: MVI da Bahia em 2025

```bash
curl 'http://localhost:8000/api/v1/registros/?uf=BA&ano=2025&indicador=mvi'
```

```json
{
  "count": 1, "next": null, "previous": null,
  "results": [{
    "id": 154,
    "ano": 2025,
    "localidade": {"nivel": "uf", "codigo": "BA", "codigo_ibge": "29", "nome": "Bahia"},
    "indicador": {"slug": "mvi", "nome": "Mortes Violentas Intencionais"},
    "recorte": null,
    "unidade": "vitimas",
    "valor": "5473",
    "situacao": "informado",
    "metodo": "publicado",
    "taxa": {"valor": "36.80", "base": "100 mil habitantes", "origem": "calculada",
             "fonte": {"id": 2, "nome": "IBGE – Estimativas da população residente"}},
    "taxa_publicada": "36.803404123232",
    "variacao": {"ano_referencia": 2024, "valor_pct": "-9.49", "taxa_pct": "-9.62"},
    "participacao": {"referencia": null, "valor_pct": null},
    "fonte": {"id": 1, "nome": "Secretarias Estaduais de Segurança Pública e/ou Defesa Social (compilação FBSP)"},
    "observacao": null
  }]
}
```

Como ler os campos:

| Campo | Significado |
| --- | --- |
| `valor` | Número absoluto, na `unidade` indicada (vítimas ou ocorrências). |
| `situacao` | `informado`; `inexistente` (o Anuário publica "-", valor 0); `nao_disponivel` (o Anuário publica "...", valor nulo). |
| `metodo` | `publicado` (lido do Anuário) ou `soma_ufs` (total regional calculado pelo projeto). |
| `taxa` | Taxa na `base` do indicador. `origem` diz se foi `calculada` com a população do IBGE ou `publicada` pelo FBSP; `fonte` é a fonte do denominador. |
| `taxa_publicada` | A taxa que o FBSP publicou, com toda a precisão guardada, para conferência. |
| `variacao` | Variação em relação a `ano_referencia`: do número absoluto (`valor_pct`) e da taxa (`taxa_pct`, a mesma coluna "Variação (%)" do Anuário). |
| `participacao` | Parte do valor no indicador-pai (ex.: mortes por intervenção policial dentro da MVI) ou, num recorte, no total do indicador. Nula quando não se aplica. |
| `fonte`, `observacao` | Fonte do valor e notas metodológicas do FBSP. |

### A série de um indicador

```bash
# MVI do Brasil, 2012 a 2025 (nível país)
curl 'http://localhost:8000/api/v1/registros/?nivel=pais&indicador=mvi'

# Feminicídio de Pernambuco de 2022 a 2025, do ano mais recente para o mais antigo
curl 'http://localhost:8000/api/v1/registros/?uf=PE&indicador=feminicidio&ordenar=-ano'
```

### Várias UFs, uma região ou todos os níveis

```bash
# Duas UFs
curl 'http://localhost:8000/api/v1/registros/?uf=SP,RJ&indicador=roubo&ano=2025'

# As UFs do Nordeste
curl 'http://localhost:8000/api/v1/registros/?nivel=uf&regiao=NE&indicador=mvi&ano=2025'

# O total do Nordeste
curl 'http://localhost:8000/api/v1/registros/?nivel=regiao&regiao=NE&indicador=mvi&ano=2025'

# Brasil, regiões e UFs juntos (precisa ser pedido explicitamente)
curl 'http://localhost:8000/api/v1/registros/?nivel=pais,regiao,uf&indicador=mvi&ano=2025'
```

Sem `nivel`, a resposta traz só as UFs. `uf` e `regiao` são parâmetros separados porque `SE` é
tanto Sergipe quanto Sudeste, e `regiao` sem `nivel` é recusado por ser ambíguo.

### Um indicador com todos os subtipos

```bash
curl 'http://localhost:8000/api/v1/registros/?uf=SP&ano=2025&indicador=roubo&incluir_subtipos=true'
```

Os subtipos **não somam** o total: uma ocorrência pode entrar em mais de um tipo de roubo. Para
furto, que não tem total, use sempre `indicador=furto&incluir_subtipos=true` ou os subtipos
diretamente (`furto-veiculo`, `furto-celular`).

### Vítimas e ocorrências

```bash
curl 'http://localhost:8000/api/v1/registros/?uf=SP&ano=2025&indicador=homicidio-doloso&unidade=todas'
# vitimas: 2527 · ocorrencias: 2438
```

Por padrão, cada indicador vem só na sua unidade principal, para que as duas contagens do mesmo crime
não se misturem. Use `unidade=ocorrencias` ou `unidade=todas` quando quiser a outra.

### Corporação e situação do policial

```bash
# Os recortes disponíveis (ids)
curl 'http://localhost:8000/api/v1/recortes/'

# Todos os recortes de mortes por intervenção policial em São Paulo
curl 'http://localhost:8000/api/v1/registros/?uf=SP&indicador=morte-intervencao-policial&recorte=todos'

# Só um recorte (ex.: id 2, Polícia Militar em serviço)
curl 'http://localhost:8000/api/v1/registros/?uf=SP&indicador=morte-intervencao-policial&recorte=2'
```

Por padrão, `/registros/` traz só o total (sem recorte), para que totais e recortes não sejam
somados juntos. Várias UFs não informam os recortes; nelas, `situacao` é `nao_disponivel`.

### Ranking das UFs

```bash
# MVI, último ano disponível, por taxa (padrões)
curl 'http://localhost:8000/api/v1/ranking/?indicador=mvi'

# Por número absoluto, em 2023
curl 'http://localhost:8000/api/v1/ranking/?indicador=mvi&ano=2023&criterio=valor'

# Quanto da MVI de cada UF é morte por intervenção policial
curl 'http://localhost:8000/api/v1/ranking/?indicador=morte-intervencao-policial&criterio=participacao'
```

A resposta repete os parâmetros usados (`indicador`, `ano`, `criterio`, `unidade`, `recorte`) e
traz `results` com as 27 UFs em ordem decrescente e a `posicao` de cada uma. Empates recebem a mesma
posição (1, 2, 2, 4), calculada sobre o valor exibido com duas casas; UFs sem dado ficam no fim, com
`posicao: null`.

### UF × região × Brasil

```bash
curl 'http://localhost:8000/api/v1/comparacao/?uf=BA&indicador=mvi&ano_min=2018'
```

Devolve `series` com três itens, sempre na ordem UF, região da UF e Brasil, cada um com `pontos` por
ano, nos mesmos anos. É o que alimenta o gráfico de evolução do painel.

### População

```bash
curl 'http://localhost:8000/api/v1/populacao/?uf=BA'
curl 'http://localhost:8000/api/v1/populacao/?nivel=pais&ano=2025'
```

### Paginação

`/registros/` e `/populacao/` devolvem 100 itens por página (`tamanho` até 1000). Siga o endereço em
`next` até ele ser `null`:

```bash
curl 'http://localhost:8000/api/v1/registros/?indicador=mvi&tamanho=1000&pagina=1'
```

Para pegar tudo de uma vez, prefira o CSV, que não é paginado.

## 4. Usar em programas

### Python (pandas)

```python
import pandas as pd

BASE = "http://localhost:8000/api/v1"

# CSV direto num DataFrame; os decimais já viram números
df = pd.read_csv(f"{BASE}/registros/?nivel=pais,regiao,uf&indicador=mvi&formato=csv")
print(df[["ano", "localidade_codigo", "valor", "taxa_valor"]].head())
```

```python
import requests
from decimal import Decimal

resposta = requests.get(f"{BASE}/ranking/", params={"indicador": "feminicidio"})
resposta.raise_for_status()
for item in resposta.json()["results"][:5]:
    print(item["posicao"], item["localidade"]["codigo"], Decimal(item["taxa"]["valor"]))
```

### R

```r
dados <- read.csv("http://localhost:8000/api/v1/ranking/?indicador=mvi&formato=csv",
                  encoding = "UTF-8")
head(dados[, c("posicao", "localidade_codigo", "taxa_valor")])
```

### JavaScript

```js
const resposta = await fetch("/api/v1/comparacao/?uf=BA&indicador=mvi");
const { series } = await resposta.json();
const pontosDaUf = series[0].pontos.map((p) => ({ ano: p.ano, taxa: Number(p.taxa.valor) }));
```

## 5. Exportar em CSV

Acrescente `formato=csv` (ou envie `Accept: text/csv`) em `/registros/`, `/populacao/`,
`/ranking/` ou `/comparacao/`. O arquivo:

- traz o recorte inteiro, sem paginação, até 50 mil linhas (acima disso, 400: filtre mais);
- usa vírgula como separador, ponto como separador decimal, UTF-8 e cabeçalho na primeira linha;
- achata os objetos em colunas unidas por `_` (`localidade_codigo`, `taxa_valor`,
  `variacao_taxa_pct`) e deixa vazio o que é nulo;
- inclui sempre as colunas de fonte (`fonte`, `taxa_fonte`) e de situação do dado.

```bash
curl -o mvi-ufs.csv 'http://localhost:8000/api/v1/registros/?indicador=mvi&formato=csv'
```

**Abrir em planilha.** Com o Excel ou o LibreOffice configurados em português, abrir o arquivo com
dois cliques pode juntar tudo numa coluna, porque eles esperam ponto e vírgula. Use a importação:

- Excel: *Dados → Obter dados → De Texto/CSV*, origem *65001: Unicode (UTF-8)*, delimitador
  *Vírgula*; em *Transformar dados*, defina a localidade *Inglês (Estados Unidos)* para as colunas
  decimais.
- LibreOffice Calc: *Arquivo → Abrir*, conjunto de caracteres *UTF-8*, separador *Vírgula* e
  idioma *Inglês (EUA)*.
- Google Planilhas: *Arquivo → Importar*, separador *Vírgula*.

## 6. Erros

Os erros seguem o padrão Problem Details (RFC 9457), sempre em JSON, mesmo quando o CSV foi pedido:

```bash
curl 'http://localhost:8000/api/v1/registros/?regiao=NE'
```

```json
{
  "type": "http://localhost:8000/api/v1/docs/erros#parametro-invalido",
  "title": "Parâmetro inválido",
  "status": 400,
  "instance": "/api/v1/registros/?regiao=NE",
  "detail": "Um ou mais parâmetros de consulta são inválidos.",
  "erros": [{"parametro": "regiao",
             "mensagem": "Ambíguo sem nivel: use nivel=uf para as UFs da região ou nivel=regiao para o agregado regional."}]
}
```

| Status | Quando |
| --- | --- |
| 400 | Parâmetro desconhecido, repetido, vazio ou inválido; combinação contraditória; CSV acima de 50 mil linhas; página além da última. |
| 404 | Item inexistente no caminho, como `/estados/XX/`. |
| 405 | Método de escrita (`POST`, `PUT`, `PATCH`, `DELETE`). |
| 406 | Formato não suportado, como CSV em `/estados/`. |
| 503 | Ainda não há dados importados no servidor. |

## 7. Cache

Os dados só mudam quando uma nova carga é importada. Por isso as respostas levam
`Cache-Control: public, max-age=86400` e um `ETag` com a versão da carga (`W/"764af7ef35c3-json"`).
Reenviar o `ETag` em `If-None-Match` devolve 304, sem corpo:

```bash
curl -i -H 'If-None-Match: W/"764af7ef35c3-json"' 'http://localhost:8000/api/v1/estados/'
# HTTP/1.1 304 Not Modified
```

A versão e a data da carga em vigor estão em `/metadados/` (`carga.versao`, `carga.concluida_em`).

## 8. Documentação interativa

| Endereço | Conteúdo |
| --- | --- |
| `/api/v1/docs/` | Swagger UI: experimente cada recurso pelo navegador. |
| `/api/v1/redoc/` | ReDoc: a mesma documentação em formato de leitura. |
| `/api/v1/schema/` | Esquema OpenAPI 3 (também versionado em [api/openapi.yaml](api/openapi.yaml)), para gerar clientes. |
