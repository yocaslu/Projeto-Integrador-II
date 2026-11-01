# Guia da API

Receitas para consultar os dados. A referência completa de cada parâmetro, formato e coluna está no
[contrato da API](contrato-api.md), e a documentação interativa, em
<http://localhost:8000/api/v1/docs/>.

A API é pública e somente leitura (`GET`, `HEAD`, `OPTIONS`), sem autenticação. Os exemplos usam o
ambiente local:

```bash
API=http://localhost:8000/api/v1
```

## Primeiros passos

**Descubra o que existe.** `/metadados/` traz a árvore de indicadores, os anos, as unidades e as fontes:

```bash
curl -s "$API/metadados/"
```

**Valor, taxa e variação de um indicador em uma UF:**

```bash
curl -s "$API/registros/?uf=BA&ano=2025&indicador=mvi"
```

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 154,
      "ano": 2025,
      "localidade": {"nivel": "uf", "codigo": "BA", "codigo_ibge": "29", "nome": "Bahia"},
      "indicador": {"slug": "mvi", "nome": "Mortes Violentas Intencionais"},
      "recorte": null,
      "unidade": "vitimas",
      "valor": "5473",
      "situacao": "informado",
      "metodo": "publicado",
      "taxa": {
        "valor": "36.80",
        "base": "100 mil habitantes",
        "origem": "calculada",
        "fonte": {"id": 2, "nome": "IBGE – Estimativas da população residente"}
      },
      "taxa_publicada": "36.803404123232",
      "variacao": {"ano_referencia": 2024, "valor_pct": "-9.49", "taxa_pct": "-9.62"},
      "participacao": {"referencia": null, "valor_pct": null},
      "fonte": {"id": 1, "nome": "Secretarias Estaduais de Segurança Pública e/ou Defesa Social (compilação FBSP)"},
      "observacao": null
    }
  ]
}
```

O `id` pode mudar em outro banco; use as chaves naturais (UF, indicador e ano).

## Receitas

| Quero… | Requisição |
| --- | --- |
| Ranking das UFs por taxa, no último ano | `/ranking/?indicador=mvi` |
| Ranking por número absoluto em um ano | `/ranking/?indicador=roubo&ano=2024&criterio=valor` |
| Peso da letalidade policial nas MVI, por UF | `/ranking/?indicador=morte-intervencao-policial&criterio=participacao` |
| Série da UF, da região e do Brasil | `/comparacao/?uf=BA&indicador=feminicidio` |
| Série histórica do Brasil | `/registros/?nivel=pais&indicador=mvi&ordenar=ano` |
| Total das regiões em um ano | `/registros/?nivel=regiao&indicador=mvi&ano=2025` |
| UFs de uma região | `/registros/?nivel=uf&regiao=NE&indicador=mvi&ano=2025` |
| Um indicador e todos os subtipos | `/registros/?uf=SP&indicador=roubo&incluir_subtipos=true&ano=2025` |
| Ocorrências, em vez de vítimas | `/registros/?uf=SP&indicador=latrocinio&unidade=ocorrencias` |
| Letalidade por corporação e situação | `/registros/?uf=SP&indicador=morte-intervencao-policial&recorte=todos&ano=2025` |
| Maiores taxas primeiro | `/registros/?indicador=mvi&ano=2025&ordenar=-taxa` |
| Só os dados não informados | `/registros/?indicador=morte-intervencao-policial&recorte=todos&situacao=nao_disponivel` |
| População usada nas taxas | `/populacao/?uf=BA&ano=2025` |

Os identificadores vêm dos catálogos: `/indicadores/`, `/estados/`, `/regioes/`, `/recortes/` e
`/fontes/`. Os slugs são:

```text
mvi                         roubo                             furto (sem registros próprios)
  homicidio-doloso            roubo-veiculo                     furto-veiculo
    homicidio-mulheres        roubo-celular                     furto-celular
      feminicidio             roubo-transeunte
  latrocinio                  roubo-residencia
  lesao-corporal-seguida-de-morte  roubo-estabelecimento-comercial
  morte-intervencao-policial  roubo-instituicao-financeira
                              roubo-carga
```

Regiões: `N`, `NE`, `SE`, `S` e `CO`; Brasil: `nivel=pais`. `SE` em `uf` é Sergipe, e em `regiao`, o
Sudeste.

## Baixar em CSV

Acrescente `formato=csv` ou envie `Accept: text/csv`. Funciona em `/registros/`, `/populacao/`,
`/ranking/` e `/comparacao/`:

```bash
curl -s "$API/registros/?indicador=mvi&ano=2025&formato=csv" -o mvi-2025.csv
```

O CSV não é paginado e vai até 50 mil linhas. Ele usa vírgula, ponto decimal e UTF-8 sem BOM, e cada
linha traz as fontes do valor e da taxa. Campos vazios correspondem a `null`.

## Usar em Python

Os decimais chegam como texto, para não perder precisão. Com o CSV, o pandas converte as colunas:

```python
import pandas as pd

API = "http://localhost:8000/api/v1"
df = pd.read_csv(f"{API}/ranking/?indicador=mvi&ano=2025&formato=csv")
print(df[["posicao", "localidade_codigo", "valor", "taxa_valor"]].head())
```

Com JSON, use `decimal.Decimal` quando a precisão importar, e `next` para percorrer as páginas:

```python
from decimal import Decimal
import requests

url = "http://localhost:8000/api/v1/registros/?indicador=mvi&ano=2025&tamanho=10"
total = Decimal(0)
while url:
    pagina = requests.get(url, timeout=30).json()
    total += sum(Decimal(r["valor"]) for r in pagina["results"] if r["valor"] is not None)
    url = pagina["next"]
print(total)
```

A soma do exemplo funciona porque, sem `nivel`, só vêm UFs. Ao somar, respeite as regras abaixo.

## Regras que evitam erros de análise

- **Por padrão, não há dupla contagem:** `/registros/` devolve só as UFs, só os totais e só a unidade
  padrão de cada indicador. Outros níveis, recortes e unidades vêm apenas quando pedidos.
- **Não some subtipos nem participações:** os subtipos não fecham o total do indicador.
- **Não some nem tire média de taxas:** use a taxa da própria região ou do Brasil.
- **`null` não é zero:** confira `situacao`. Em `inexistente` o valor é `0`; em `nao_disponivel`, é `null`.
- **`metodo=soma_ufs`** indica um total regional calculado pelo projeto, e não publicado pelo FBSP.
- **`variacao.taxa_pct`** é a variação da taxa, comparável à coluna do FBSP; `valor_pct` é a do número
  absoluto.

## Erros

Todo erro sai em JSON (Problem Details, RFC 9457), mesmo quando se pede CSV. Parâmetros desconhecidos
ou inválidos não são ignorados, para que um erro de digitação não devolva outros dados:

```bash
curl -s "$API/registros/?uf=XX"
```

```json
{
  "type": "http://localhost:8000/api/v1/docs/erros#parametro-invalido",
  "title": "Parâmetro inválido",
  "status": 400,
  "instance": "/api/v1/registros/?uf=XX",
  "detail": "Um ou mais parâmetros de consulta são inválidos.",
  "erros": [{"parametro": "uf", "mensagem": "Valor não reconhecido: XX."}]
}
```

| Status | Causa comum | O que fazer |
| --- | --- | --- |
| 400 | Parâmetro desconhecido, repetido ou vazio, valor inexistente, combinação proibida (`uf` com `regiao`, `regiao` sem `nivel`, `indicador=furto` sem `incluir_subtipos`), mais de 50 mil linhas no CSV | Leia a lista `erros` |
| 404 | UF, região, indicador ou registro inexistente no caminho, como `/estados/XX/` | Confira o catálogo |
| 405 | Método de escrita | A API é somente leitura |
| 406 | CSV em recurso sem CSV, como `/estados/?formato=csv`, ou formato desconhecido | Use JSON |
| 503 | Nenhuma importação concluída | [Importe os dados](guia-de-operacao.md#importar-os-dados) |

## Paginação e cache

`/registros/` e `/populacao/` têm `pagina` (padrão 1) e `tamanho` (padrão 100, máximo 1000). Os demais
recursos devolvem tudo de uma vez.

Os dados só mudam em uma nova importação. As respostas podem ficar em cache por um dia e trazem um
`ETag`; reenvie-o para receber 304, sem corpo, se nada mudou:

```bash
curl -s -o /dev/null -w '%{http_code}\n' -H 'If-None-Match: W/"764af7ef35c3-json"' "$API/estados/"
```

O valor do `ETag` depende da carga: pegue-o no cabeçalho da resposta anterior.

## Citar os dados

`carga.versao`, em `/metadados/`, identifica a carga usada. Cite as fontes de `fonte` e `taxa.fonte` e o
Anuário Brasileiro de Segurança Pública, do FBSP. Uma mudança incompatível na API daria origem a
`/api/v2/`, com a v1 mantida.
