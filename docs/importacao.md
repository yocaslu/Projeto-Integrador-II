# Importação da planilha do FBSP

Especificação do comando `importar_anuario`: o que se extrai de `dados/brutos/anuario-2026.xlsx` (20º Anuário, FBSP 2026) e das estimativas do IBGE (`POP2024_20241230.ods`, `POP2025_20260828.ods`), como cada tabela é lida e como os dados são gravados.

Mapeamento levantado na planilha versionada (SHA-256 `6b01f4ed…784f21`). Se o hash mudar, rode `inspecionar_planilha` e confira este documento antes de importar.

---

## 1. Estrutura da planilha

A planilha tem 134 abas. Os nomes seguem um prefixo:

| Prefixo | Conteúdo | Importação |
| :--- | :--- | :--- |
| `T01`…`T95` | Tabelas por UF (cabeçalho em 2 a 4 níveis, células mescladas) | Só as listadas na seção 3 |
| `P01`…`P11` | Painéis: blocos de dados de gráficos, sem cabeçalho tabular | Não (ver Pendência 2 no CLAUDE.md) |
| `G..` | Gráficos | Não |
| `Q..` | Quadros (rankings municipais etc.) | Não |
| `Índice` | Índice da publicação | Não |

Padrão das tabelas por UF (verificado em T01–T21):

- Linha 1: `TABELA nn`; linha 2: título; linha 3: abrangência e período.
- Linha 5: âncora na coluna A (`Brasil e Unidades da Federação` ou `Brasil, Regiões e Unidades da Federação`; às vezes com espaço inicial). A linha 3 começa com o mesmo texto (`Brasil e Unidades da Federação – 2024-2025`), por isso a regex da âncora é fechada com `\s*$` (seção 4.2).
- Linhas seguintes do cabeçalho:
  - bloco (indicador ou recorte);
  - sub-bloco (ex.: `Nº de Vítimas`);
  - grupo: `Ns. Absolutos`, `Taxa (n)` / `Taxas (n)`, `Variação (%)` (às vezes com quebra de linha);
  - ano: inteiro ou texto com marca, ex. `2024 (3)`.
- Dados: `Brasil` primeiro, depois as UFs em ordem alfabética. Na T02, regiões (`Região Norte`, …) aparecem seguidas de suas UFs, com **linhas em branco entre os grupos**.
- Rodapé: uma linha `Fonte: …` (na T15 o prefixo vem duplicado, `Fonte: Fonte: …`), depois a legenda (`(-) Fenômeno Inexistente.`, `(...) Informação não disponível.`) e as notas numeradas `(1) …`, `(2) …`.
- Marcas de nota aparecem no rótulo da linha (`Minas Gerais (4)`), no grupo (`Taxa (2)`) e no ano (`2024 (3)`). Um rótulo pode ter mais de uma marca: `Rio Grande do Norte (3) (4)` na T05.
- Valores numéricos vêm como `int` ou `float`. Taxas e variações **não são arredondadas** (ex.: `19.105426800076884`).
- Textos encontrados nas áreas de dados: apenas `-` e `...`. Não há células vazias nas tabelas importadas.

---

## 2. Indicadores (`catalogo/referencia.py`)

| Ordem | Slug | Nome | Pai | Unidade padrão | Base da taxa | Tabela dona |
| ---: | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `mvi` | Mortes Violentas Intencionais | — | vítimas | 100 mil habitantes | T02 |
| 2 | `homicidio-doloso` | Homicídio doloso | `mvi` | vítimas | 100 mil habitantes | T03 |
| 3 | `homicidio-mulheres` | Homicídio de mulheres (incluindo feminicídios) | `homicidio-doloso` | vítimas | 100 mil mulheres | T21 |
| 4 | `feminicidio` | Feminicídio | `homicidio-mulheres` | vítimas | 100 mil mulheres | T21 |
| 5 | `latrocinio` | Latrocínio | `mvi` | vítimas | 100 mil habitantes | T04 |
| 6 | `lesao-corporal-seguida-de-morte` | Lesão corporal seguida de morte | `mvi` | vítimas | 100 mil habitantes | T05 |
| 7 | `morte-intervencao-policial` | Morte decorrente de intervenção policial | `mvi` | vítimas | 100 mil habitantes | T08 |
| 8 | `roubo` | Roubo (total) | — | ocorrências | 100 mil habitantes | T15 |
| 9 | `roubo-veiculo` | Roubo de veículo | `roubo` | ocorrências | 100 mil veículos | T11 |
| 10 | `roubo-celular` | Roubo de celular | `roubo` | ocorrências | 100 mil habitantes | T12 |
| 11 | `roubo-transeunte` | Roubo a transeunte | `roubo` | ocorrências | 100 mil habitantes | T14 |
| 12 | `roubo-residencia` | Roubo a residência | `roubo` | ocorrências | 100 mil habitantes | T14 |
| 13 | `roubo-estabelecimento-comercial` | Roubo a estabelecimento comercial | `roubo` | ocorrências | 100 mil habitantes | T14 |
| 14 | `roubo-instituicao-financeira` | Roubo a instituição financeira | `roubo` | ocorrências | 100 instituições | T15 |
| 15 | `roubo-carga` | Roubo de carga | `roubo` | ocorrências | 100 mil habitantes | T15 |
| 16 | `furto` | Furto | — | ocorrências | — | **sem registros** |
| 17 | `furto-veiculo` | Furto de veículo | `furto` | ocorrências | 100 mil veículos | T11 |
| 18 | `furto-celular` | Furto de celular | `furto` | ocorrências | 100 mil habitantes | T12 |

- `unidade_padrao` é a unidade que a API usa quando o cliente não pede outra. A unidade de cada valor fica no próprio registro (`REGISTROS_ANUAIS.unidade`, `vitimas` | `ocorrencias`, ADR 0004). `homicidio-doloso`, `latrocinio` e `lesao-corporal-seguida-de-morte` têm registros nas duas unidades (T03–T05); os demais, só na unidade padrão.
- `ordem` é a pré-ordem da hierarquia, usada pela API para ordenar indicadores (`INDICADORES.ordem`, inteiro único).
- Hierarquia (ADR 0003): `feminicidio` é filho de `homicidio-mulheres`, que é filho de `homicidio-doloso`. A T03 define homicídio doloso como "incluindo feminicídios", e a T21 publica a "proporção de feminicídios em relação aos homicídios de mulheres". A hierarquia significa "contido em", nunca "soma de".

Localidades (`localidades/referencia.py`), com os códigos do IBGE em texto:

| Tipo | Sigla | Nome | `codigo_ibge` |
| :--- | :--- | :--- | :--- |
| `pais` | `BR` | Brasil | `1` |
| `regiao` | `N`, `NE`, `SE`, `S`, `CO` | Norte, Nordeste, Sudeste, Sul, Centro-Oeste | `1` a `5` |
| UF | `RO` … `DF` | nome oficial | `11` … `53` (2 dígitos) |

Fontes (`catalogo/referencia.py`, ADR 0005), criadas antes das demais referências, nesta ordem, com `update_or_create(slug=…)`, para que um banco limpo reproduza os mesmos `id`s:

| `id` | `slug` | Nome | Usada em |
| ---: | :--- | :--- | :--- |
| 1 | `secretarias-seguranca` | Secretarias Estaduais de Segurança Pública e/ou Defesa Social (compilação FBSP) | `fonte` de todos os registros, inclusive `soma_ufs` |
| 2 | `ibge-estimativas` | IBGE – Estimativas da população residente | `fonte` da `POPULACAO`; `fonte_taxa` da base 100 mil habitantes |
| 3 | `ibge-projecoes` | IBGE – Projeções da população | `fonte_taxa` da base 100 mil mulheres (T21) |
| 4 | `senatran-frota` | Senatran – Frota de veículos | `fonte_taxa` da base 100 mil veículos (T11, nota 2) |
| 5 | `bcb-instituicoes` | Banco Central do Brasil – Instituições financeiras | `fonte_taxa` da base 100 instituições (T15, nota 3) |

- Cada indicador recebe `fonte_taxa` junto com `base_taxa` (nula só em `furto`, que não tem base). É de lá que a API tira `taxa.fonte`.
- A linha "Fonte:" completa de cada tabela fica no relatório, não em cada registro. Descrições e URLs das fontes: ADR 0005.

---

## 3. Mapeamento por tabela

Linhas e colunas abaixo são as observadas hoje, para conferência. **O código não usa posições fixas**: localiza a âncora e resolve cada coluna pelo caminho do cabeçalho (seção 4.2).

Só a T02 publica totais regionais. Nas demais tabelas (28 localidades: Brasil e 27 UFs), os cinco totais regionais são **calculados** como soma das UFs (seção 4.8), o que acrescenta 5 registros por (indicador, recorte, ano). As contagens abaixo trazem as duas parcelas: lidos + calculados.

### T02 — Série histórica de MVI (dona de `mvi`)
- Cabeçalho nas linhas 5–7; dados nas linhas 9–46, com 33 localidades (Brasil, 5 regiões e 27 UFs).
- `B:O` → `valor` de 2012 a 2025; `P:AC` → `taxa_publicada` de 2012 a 2025 (por 100 mil habitantes).
- Gera 33 × 14 = **462** registros.

### T01 — MVI 2024–2025 (só conferência)
- `L:M` (valor) e `N:O` (taxa) de MVI. Hoje são idênticos à T02 em todas as 28 localidades.
- Os outros blocos (CVLI, policiais vítimas, MDIP) não são lidos: têm tabelas próprias.
- Divergência T01 × T02 entra no relatório como **divergência**.

### T03, T04, T05 — Homicídio doloso, latrocínio, lesão corporal seguida de morte
- Cabeçalho nas linhas 5–8; dados nas linhas 10–38 (28 localidades).
- Sub-bloco `Nº de Vítimas` (`unidade = vitimas`): `B:C` → valor 2024/2025; `D:E` → taxa 2024/2025; `F` → variação (só validação).
- Sub-bloco `Nº de Ocorrências` (`unidade = ocorrencias`, ADR 0004): `G:H` → valor 2024/2025; `I:J` → taxa por 100 mil habitantes 2024/2025; `K` → variação (só validação).
- Nas ocorrências não há "..." nem "-", e o Brasil é exatamente a soma das UFs nos dois anos.
- Uma unidade preenchida com a outra, por falta do dado (vai para `observacao` pela marca da linha): PI, RJ, RN e RR têm ocorrências = vítimas (T03 nota 5, T04 nota 3, T05 nota 3); SP tem vítimas de lesão corporal seguida de morte = ocorrências (T05 nota 5).
- Gera 3 × 2 unidades × 56 = 336 lidos + 3 × 2 × 10 = 60 regionais = **396** registros.

### T08 — Mortes decorrentes de intervenção policial
- Cabeçalho nas linhas 5–7; dados nas linhas 9–37.
- Colunas e recortes:

| Colunas | Bloco | Recorte | Grava |
| :--- | :--- | :--- | :--- |
| `B:C` | Intervenções de Policiais Civis em serviço | `corporacao=Polícia Civil; situacao_policial=Em serviço` | valor |
| `D:E` | Intervenções de Policiais Militares em serviço | `corporacao=Polícia Militar; situacao_policial=Em serviço` | valor |
| `F:G` | Intervenções de Policiais Civis fora de serviço | `corporacao=Polícia Civil; situacao_policial=Fora de serviço` | valor |
| `H:I` | Intervenções de Policiais Militares fora de serviço | `corporacao=Polícia Militar; situacao_policial=Fora de serviço` | valor |
| `J:K` + `L:M` | Total | sem recorte | valor + taxa |

- A soma dos recortes pode não bater com o total: há "..." e mortes em operações conjuntas (nota 5, Sergipe). A comparação entra no relatório como **informação**.
- Amapá, Pará, Bahia, Rio Grande do Norte e Rio de Janeiro trazem "..." nos quatro recortes, nos dois anos (Sergipe também, exceto em serviço de 2025). O total sem recorte está completo. O FBSP publica o Brasil desses recortes como **soma parcial** das UFs que informaram; ele é importado como está e a situação entra no relatório como informação. Norte, Nordeste e Sudeste ficam `nao_disponivel` nesses recortes (seção 4.8): 4 recortes × 2 anos × 3 regiões = 24 registros.
- Gera 5 × 56 = 280 lidos + 5 × 10 = 50 regionais = **330** registros.

### T09 — Proporção de MDIP em relação às MVI (só conferência)
- Não grava registros: a proporção é calculada pela API (`participacao`, ADR 0004).
- `B:C` (MVI) e `D:E` (MDIP) são conferidos contra a T02 e o total da T08; `F:G` (percentual) contra a participação calculada (MDIP ÷ MVI × 100). Hoje batem em todas as 28 localidades.
- Divergência entra no relatório como **divergência**.

### T11 — Roubo e furto de veículos
- `B:C`/`D:E` → `roubo-veiculo`; `G:H`/`I:J` → `furto-veiculo`. Taxa por 100 mil veículos (Senatran, nota 2).
- O bloco `Roubo e Furto de Veículo` (`L:P`) **não é importado** (regra 5).
- Os totais regionais não têm taxa: não há frota de veículos por região.
- Gera 112 lidos + 20 regionais = **132** registros.

### T12 — Roubo e furto de celulares (ocorrências)
- `B:C`/`D:E` → `roubo-celular`; `G:H`/`I:J` → `furto-celular`. Taxa por 100 mil habitantes.
- O bloco combinado `L:P` **não é importado**. A T13 (quantidade de aparelhos) também não.
- Gera 112 lidos + 20 regionais = **132** registros.

### T14 — Roubo a estabelecimento comercial, residência e transeunte
- `B:C`/`D:E` → `roubo-estabelecimento-comercial`; `G:H`/`I:J` → `roubo-residencia`; `L:M`/`N:O` → `roubo-transeunte`.
- Gera 168 lidos + 30 regionais = **198** registros.

### T15 — Roubo a instituição financeira, de carga e total
- `B:C`/`D:E` → `roubo-instituicao-financeira` (taxa por 100 instituições, Banco Central, nota 3).
- `G:H`/`I:J` → `roubo-carga`.
- `L:M`/`N:O` → `roubo`. Nota 1: o total pode ser menor que a soma dos subtipos, e por isso o total é importado, nunca somado. O total regional de `roubo` é a soma das UFs no próprio `roubo`, e não a soma dos subtipos da região.
- Os totais regionais de `roubo-instituicao-financeira` não têm taxa: não há número de instituições por região.
- Gera 168 lidos + 30 regionais = **198** registros.

### T21 — Homicídio de mulheres e feminicídio
- Cabeçalho nas linhas 5–8; dados nas linhas 10–38.
- `B:C`/`D:E` → `homicidio-mulheres`; `G:H`/`I:J` → `feminicidio`. Taxa por 100 mil mulheres (nota 2).
- A coluna de proporção (`L:M`, percentual) **não é importada**: é calculada pela API como participação do feminicídio no homicídio de mulheres (ADR 0004) e lida só como **conferência** contra esse cálculo.
- Os totais regionais não têm taxa: a população feminina por região não está em `POPULACAO`.
- Gera 112 lidos + 20 regionais = **132** registros.

### Totais esperados

| Item | Quantidade |
| :--- | ---: |
| Registros lidos da planilha (`metodo = publicado`) | 1.750 |
| Registros regionais calculados (`metodo = soma_ufs`, seção 4.8) | 230 |
| **Registros (`REGISTROS_ANUAIS`)** | **1.980** |
| Recortes (`RECORTES`) | 4 |
| População (`POPULACAO`) | 66 (33 localidades × 2 anos) |

Os 230 calculados são 46 combinações (indicador, recorte, unidade, ano) das tabelas T03–T21, cada uma em 5 regiões. A MVI não entra na conta porque a T02 já publica as regiões. Dos 230, 24 ficam nulos (`nao_disponivel`): os quatro recortes de corporação e situação da T08 no Norte, Nordeste e Sudeste, em 2024 e 2025.

---

## 4. Algoritmo

### 4.1 Fluxo do comando

```
importar_anuario [--dados DIR] [--relatorio DIR] [--manifesto ARQ] [--somente-validar] [--estrito]
│
├─ 1. verificar_arquivos(DIR, ARQ)            → todo arquivo do manifesto (padrão: README.md acima de DIR,
│                                               isto é, dados/README.md) existe com o mesmo SHA-256; senão → CommandError
├─ 2. versao = sha256(concat(hashes, em ordem de nome))[:12]
├─ 3. carga = Carga(versao, arquivos, status="em_andamento")   # não é criada com --somente-validar
├─ 4. with transaction.atomic():
│     ├─ carregar_referencias()                 # fontes (primeiro, ordem fixa), regiões, UFs, indicadores (update_or_create)
│     ├─ populacoes = [ibge.ler(ods) ...]       # 33 localidades por ano; 66 linhas
│     ├─ gravar_populacao(populacoes)
│     ├─ lidas = [fbsp.ler_tabela(wb, t) for t in TABELAS]   # linhas das donas + valores publicados (variação, proporção, T01, T09)
│     ├─ linhas += agregacao.agregar(linhas, regiao_da_uf)  # seção 4.8; somável pela unidade da chave; diverge → CommandError
│     ├─ verificar_chaves_unicas(linhas)        # mesma chave vinda de duas tabelas donas → erro
│     ├─ conferir contagem: lidos e calculados = mapeamento.contagem_esperada()  # 1.750 + 230
│     ├─ relatorio = validacao.gerar(linhas, lidas, populacoes, ...)
│     ├─ if --somente-validar: desfaz a transação (transaction.set_rollback(True)) e não grava
│     ├─ orfaos = gravacao.upsert(linhas, refs, ordem_recortes)   # recortes na ordem dos blocos
│     └─ carga: status="concluida", concluida_em, total_registros
├─ 5. relatorio.salvar(--relatorio, versao)
└─ 6. if --estrito and relatorio.tem_divergencias: CommandError (código ≠ 0)
```

O fluxo está em `apps/importacao/processo.py` (`importar`), que recebe as tabelas como parâmetro para que os testes usem as planilhas reduzidas; o comando só trata opções e mensagens. Qualquer exceção desfaz a transação inteira, a carga fica com `status = falhou`, e a carga anterior continua valendo. Com `--estrito`, a carga já foi gravada quando o comando termina com erro: a opção serve para o CI ou um script notarem a divergência.

### 4.2 Especificação declarativa (`mapeamento.py`)

Cada coluna é identificada pelo seu **caminho de cabeçalho**: a lista de textos das linhas de cabeçalho acima dela, com as células mescladas expandidas. Exemplo da coluna `D` da T03:

```
("Homicídios dolosos", "Nº de Vítimas", "Taxas (2)", "2024 (3)")
```

```python
@dataclass(frozen=True)
class Bloco:
    indicador: str                              # slug
    caminho: tuple[str, ...]                    # regexes que precisam casar, em ordem, com o caminho
    recorte: tuple[tuple[str, str], ...] = ()   # pares (dimensao, valor); vazio = total
    unidade: str | None = None                  # vitimas | ocorrencias; None = unidade_padrao do indicador
    grupos: frozenset[str] = frozenset({"valor", "taxa"})

@dataclass(frozen=True)
class Tabela:
    aba: str
    ancora: str                                 # regex do rótulo da coluna A que abre o cabeçalho
    linhas_cabecalho: int                       # níveis abaixo da âncora, inclusive
    blocos: tuple[Bloco, ...]
    anos: tuple[int, ...]
    localidades_esperadas: int                  # 28 ou 33
    conferencia: bool = False                   # True = só alimenta o relatório (T01, T09)

ANCORA_UFS = r"^\s*Brasil e Unidades da Federa[çc][ãa]o\s*$"
ANCORA_REGIOES = r"^\s*Brasil, Regi[õo]es e Unidades da Federa[çc][ãa]o\s*$"
# Fechadas com \s*$: a linha 3 (abrangência) começa com o mesmo texto e vem antes da âncora.

GRUPOS = {r"^ns\.? absolutos|^n[úu]mero absoluto": "valor",
          r"^taxas?\b": "taxa",
          r"^varia[çc][ãa]o": "variacao",
          r"^em percentual|^propor[çc][ãa]o": "proporcao"}   # só conferência (T09, T21)

TABELAS = (
    Tabela(
        aba="T02", ancora=ANCORA_REGIOES, linhas_cabecalho=3,
        blocos=(Bloco("mvi", (r"Mortes Violentas Intencionais",)),),
        anos=tuple(range(2012, 2026)), localidades_esperadas=33,
    ),
    Tabela(
        aba="T03", ancora=ANCORA_UFS, linhas_cabecalho=4,
        blocos=(
            Bloco("homicidio-doloso", (r"Homic[íi]dios dolosos", r"V[íi]timas"), unidade="vitimas"),
            Bloco("homicidio-doloso", (r"Homic[íi]dios dolosos", r"Ocorr[êe]ncias"), unidade="ocorrencias"),
        ),
        anos=(2024, 2025), localidades_esperadas=28,
    ),
    Tabela(
        aba="T08", ancora=ANCORA_UFS, linhas_cabecalho=3,
        blocos=(
            Bloco("morte-intervencao-policial", (r"Policiais Civis em servi[çc]o",),
                  recorte=(("corporacao", "Polícia Civil"), ("situacao_policial", "Em serviço")),
                  grupos=frozenset({"valor"})),
            # ... PM em serviço, PC fora, PM fora
            Bloco("morte-intervencao-policial", (r"^Total$",)),
        ),
        anos=(2024, 2025), localidades_esperadas=28,
    ),
    # T04, T05 (vítimas e ocorrências, como a T03), T11, T12, T14, T15, T21 e T01, T09 (conferencia=True) — ver seção 3
)
```

Regras:
- Nenhuma posição fixa de linha ou coluna. Mudou o layout? O teste contra a planilha real quebra e aponta a tabela.
- A âncora é ancorada nos dois lados (`^…$`). Sem o `$`, ela casaria com a linha 3 (`Brasil e Unidades da Federação – 2024-2025`) e o cabeçalho seria lido duas linhas acima do lugar. Há teste: em cada tabela, a âncora fica na linha 5.
- Toda coluna dentro da largura do cabeçalho precisa casar com exatamente um bloco **ou** estar listada como ignorada (`ignorar=(r"Roubo e Furto",)`). Uma coluna órfã aborta a importação.
- Todo slug usado precisa existir em `catalogo/referencia.py` (há teste para isso).

### 4.3 Leitura de uma tabela

```python
def ler_tabela(wb, t: Tabela) -> list[Linha]:
    ws = wb[t.aba]                                    # load_workbook(data_only=True), sem read_only: precisa de merged_cells
    grade = expandir_mescladas(ws)                    # valor da célula superior esquerda replicado no intervalo
    r_ancora = achar_ancora(grade, t.ancora)          # 1ª linha cuja coluna A casa a regex inteira (^…$)
    colunas = resolver_colunas(grade, r_ancora, t)    # {col: (bloco, grupo, ano, marcas)}; órfã → erro
    notas = ler_notas(grade)                          # {"3": "Atualização das informações ..."}
    linhas: dict[Chave, Linha] = {}
    for r in range(r_ancora + t.linhas_cabecalho, grade.max_row + 1):
        rotulo = grade[r][0]
        if vazio(rotulo):
            continue                                  # T02 tem linhas em branco entre regiões
        if re.match(r"^\s*Fonte:", str(rotulo)):
            break                                     # fim da área de dados
        nome, marcas_linha = separar_marcas(rotulo)   # "Rio Grande do Norte (3) (4)" → ("Rio Grande do Norte", ["3", "4"])
        localidade = resolver_localidade(nome)        # desconhecida → ErroImportacao(aba, r)
        for col, (bloco, grupo, ano, marcas_col) in colunas.items():
            if grupo in ("variacao", "proporcao"):
                continue                              # vão para a validação, não para o banco
            celula = normalizar_celula(grade[r][col])
            unidade = bloco.unidade or unidade_padrao[bloco.indicador]
            linha = linhas.setdefault(Chave(localidade, bloco.indicador, bloco.recorte, unidade, ano), Linha(...))
            if grupo == "valor":
                linha.valor, linha.situacao = celula.valor, celula.situacao
                linha.origem = f"{t.aba}!{coord(r, col)}"
            else:
                linha.taxa_publicada = celula.valor
            linha.marcas |= set(marcas_linha + marcas_col)
    for linha in linhas.values():
        linha.observacao = juntar_notas(notas, linha.marcas, ignorar=NOTAS_GENERICAS)
    conferir_contagem(linhas, t)                      # localidades × anos × blocos (cada unidade é um bloco)
    return list(linhas.values())
```

`resolver_colunas`:
- Monta o caminho de cada coluna nas `linhas_cabecalho` abaixo da âncora (inclusive).
- Classifica o grupo pelo penúltimo nível com `GRUPOS`.
- Extrai o ano do último nível com `^(\d{4})`; o restante do texto vira marca (`"2024 (3)"` → `2024`, `["3"]`).
- Também extrai marcas do grupo (`"Taxa (2)"` → `["2"]`).
- Confere a base de cada grupo de taxa pelo próprio cabeçalho. O texto que declara a base é:
  - o **rótulo do grupo**, quando ele não tem marca de nota (`Taxas por 100 mil habitantes`, T02);
  - senão, o **texto da nota cuja marca está no grupo**, qualquer que seja o número: `Taxa (2)` → nota (2) em T01, T03, T08, T11, T12 e T21; `Taxa (1)` → nota (1) em T04, T05 e T14; na T15, `Taxa (3)` (instituição financeira) → nota (3) e `Taxa (4)` (carga e total) → nota (4), enquanto a nota (2) da T15 é uma definição de instituição financeira.

  Esse texto precisa conter a `base_taxa` do indicador do bloco (`100 mil habitantes`, `100 mil mulheres`, `100 mil veículos`, `100 instituições`), comparado sem acento, sem diferença de caixa e com espaços normalizados (`Taxa por 100 instituições financeiras` casa com `100 instituições`). Grupo de taxa sem base no rótulo e sem marca, marca sem nota correspondente ou base diferente abortam a importação; é a proteção contra blocos trocados entre edições. Nunca se procura uma nota de número fixo. Conferido na planilha versionada: todas as colunas de taxa das tabelas lidas passam.

`NOTAS_GENERICAS`: notas que não descrevem o dado e não vão para `observacao`, como "Taxa por 100 mil habitantes". A nota "Atualização das informações publicadas no Anuário…" **vai**, porque informa que o valor de 2024 foi revisado (RF11).

### 4.4 Normalização de célula

Já implementada em `apps/importacao/normalizacao.py` (`normalizar_celula`):

| Conteúdo | `valor` | `situacao` |
| :--- | :--- | :--- |
| `int` / `float` | `Decimal(str(v))` | `informado` |
| `-`, `–`, `—` | `0` | `inexistente` |
| `...`, `…` | `NULL` | `nao_disponivel` |
| vazio / `None` / NaN | `NULL` | `nao_disponivel` + aviso no relatório |
| qualquer outro texto | — | `ValueError` → aborta com a coordenada |

Taxa com `-` grava `taxa_publicada = 0`; com `...`, `NULL`.

Taxa numérica: `Decimal(str(v)).quantize(Decimal("1e-12"), rounding=ROUND_HALF_UP)`, o mesmo arredondamento que o PostgreSQL faria ao gravar em `NUMERIC(24, 12)`. Feito aqui, e não deixado para o banco, a `Linha` em memória fica igual ao valor gravado, e a validação e a idempotência comparam os mesmos números. A planilha traz até 17 dígitos significativos (até 18 casas), que são a representação em ponto flutuante do Excel; o erro de até 5e-13 é irrelevante, mas diferenças menores que isso entre a taxa calculada e a publicada não aparecem no relatório (ADR 0003). Nunca `Decimal(v)` direto do `float`: ele produziria a expansão binária inteira.

### 4.5 Localidades

```python
def chave(nome: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", sem_acento).strip().lower()
```

- Aliases vêm de `localidades/referencia.py`: nome de cada UF, `brasil`, e cada região em duas formas (`regiao norte` na planilha do FBSP, `norte` na do IBGE; `centro-oeste` também sem hífen).
- Rótulo fora dos aliases → erro com aba e linha. Nada de correspondência aproximada: um nome novo entra no dicionário por PR.

### 4.6 Recortes

```python
def obter_recorte(itens: tuple[tuple[str, str], ...]) -> Recorte | None:
    if not itens:
        return None                                   # total do indicador
    chave = ";".join(f"{d}={v}" for d, v in sorted(itens))
    recorte, criado = Recorte.objects.get_or_create(chave=chave, defaults={"rotulo": rotulo_de(itens)})
    if criado:
        RecorteItem.objects.bulk_create(RecorteItem(recorte=recorte, dimensao=d, valor=v) for d, v in itens)
    return recorte
```

Dimensões permitidas: `corporacao` e `situacao_policial`. Perfis de vítimas (sexo, raça/cor, faixa etária) estão fora do escopo (ADR 0004).

Os recortes são criados na ordem dos blocos em `mapeamento.py` (`gravacao.obter_recortes`), de modo que um banco limpo reproduz os mesmos `id`s (contrato, 4.4): 1 Polícia Civil, em serviço; 2 Polícia Militar, em serviço; 3 Polícia Civil, fora de serviço; 4 Polícia Militar, fora de serviço. O `rotulo` junta os valores na ordem da chave, só o primeiro com maiúscula.

### 4.7 IBGE

- Aba `BRASIL_E_UFs` de cada `.ods`, lida com `pandas.read_excel(..., engine="odf", header=None, dtype=object)`.
- O ano vem do título (`... DATA DE REFERÊNCIA EM 1º DE JULHO DE 2025`), conferido com o nome do arquivo.
- Âncora: linha `BRASIL E UNIDADES DA FEDERAÇÃO`. Leitura até `Fonte:`.
- Esperado por ano: 33 linhas (Brasil, 5 regiões e 27 UFs, com os totais regionais já publicados; não há soma).
- A terceira coluna, com marcas de nota (ex.: `(1)` em PR e SC em 2025), é ignorada no valor e registrada no relatório.
- As taxas do FBSP batem com essa população com diferença < 1e-13; por isso a validação usa tolerância de 1e-6, sem arredondar (seção 5, ADR 0004).

### 4.8 Totais regionais (`agregacao.py`)

Decisão registrada no ADR 0002. O Anuário publica o total do Brasil em todas as tabelas, mas os totais das regiões só na T02 (MVI). Sem eles, `nivel=regiao` e `/comparacao/` (RF13) ficariam vazios para todos os indicadores menos a MVI. A região é então calculada como **soma das UFs**, que é o mesmo método do FBSP.

**Premissa conferida na planilha versionada:**

- em todas as colunas de números absolutos de T01 a T21 (vítimas e ocorrências), o Brasil é exatamente a soma das 27 UFs;
- na T02, cada região é exatamente a soma das suas UFs, em todos os 14 anos;
- as únicas diferenças estão em colunas de taxa, variação e proporção, que não são somáveis.

Implementação (`agregacao.agregar`, já escrita e testada em `tests/importacao/test_agregacao.py`):

```python
def agregar(linhas, regiao_da_uf) -> list[Linha]:
    """Confere os agregados publicados e devolve as linhas regionais que faltam."""
    # 1. Brasil (todas as tabelas): soma das UFs que informaram == valor publicado, senão ErroAgregacao.
    #    Se alguma UF estiver "...", anota em observacao que o total publicado é soma parcial.
    # 2. Para cada (região, indicador, recorte, unidade, ano) de UFs com unidade somável:
    #    - região já publicada (T02) → só conferência (diverge → ErroAgregacao);
    #    - senão → _somar(ufs), com metodo = soma_ufs.
    # 3. Qualquer divergência acumulada → ErroAgregacao com todas listadas.

def _somar(chave, ufs) -> Linha:
    if any(u.valor is None for u in ufs):
        valor, situacao = None, "nao_disponivel"            # nunca soma parcial
    elif all(u.situacao == "inexistente" for u in ufs):
        valor, situacao = Decimal(0), "inexistente"
    else:
        valor, situacao = sum(u.valor for u in ufs), "informado"
    return Linha(chave=chave, valor=valor, situacao=situacao, metodo="soma_ufs",
                 taxa_publicada=None,
                 origem=_origem(ufs),                         # "T03!C19+C24+C30+C36"
                 observacao=NOTA_SOMA + UFs sem informação + notas das UFs,
                 marcas=união das marcas das UFs)
```

Regras:

| Situação | Resultado |
| :--- | :--- |
| Linha de UF (unidade `vitimas` ou `ocorrencias`, a da chave) | Somada com as demais UFs da região, no mesmo indicador, recorte, unidade e ano |
| Indicador-pai × subtipos | Nunca somados entre si: a soma é só geográfica (UF → região) |
| Todas as UFs da região informadas | `valor` = soma; `situacao = informado` (ou `inexistente`, se todas forem "-") |
| Alguma UF da região com "..." | `valor = NULL`, `situacao = nao_disponivel`; a observação lista as UFs sem informação. Nunca grava soma parcial |
| Região já publicada (T02) | Não é recalculada; vira conferência |
| Agregado publicado (Brasil ou região da T02) diferente da soma das UFs que informaram | `ErroAgregacao` → a importação aborta |
| Brasil publicado com UF "..." | Mantido como publicado (o FBSP soma só as UFs que informaram) e anotado em `observacao`: "O total publicado pelo FBSP soma apenas as UFs que informaram o dado (21 de 27; sem informação: …)." Também entra no relatório como **informação** (hoje, o Brasil dos recortes da T08) |
| UF ausente no grupo ou UF sem região | `ErroAgregacao` (regra 7) |

Campos da linha regional:

- `metodo = soma_ufs` (as lidas da planilha têm `metodo = publicado`). A API expõe o campo para que o dashboard identifique o valor como calculado pelo projeto (RF11).
- `taxa_publicada = NULL`. A taxa da região é calculada na consulta pela população da região quando a base é 100 mil habitantes (regra 11). Nas demais bases (mulheres, veículos, instituições) não há denominador regional, e a taxa fica nula. Taxas das UFs nunca são somadas nem tiradas em média.
- `origem` = as células somadas, com a aba uma vez: `T03!C19+C24+C30+C36`.
- `observacao` = "Valor calculado pelo projeto como soma das UFs da região.", seguida, quando houver, de "UFs sem informação: …" e das notas das UFs. **Não é nula**: as notas das UFs (RF11) valem também para o total que as soma. Uma nota comum a todas as UFs aparece uma vez; as demais vêm com a sigla da UF (ex.: `MG: A categoria homicídio doloso inclui as mortes decorrentes de intervenções policiais.`).
- `marcas` = união das marcas das UFs.
- `fonte` é a mesma das UFs somadas (atribuída na gravação).

A função recebe a referência por parâmetro (`regiao_da_uf`, de `localidades/referencia.py`) e não acessa o banco; o que é somável decide-se pela `unidade` da chave (ADR 0004). `linhas.Chave` tem `unidade`, e uma linha de UF com unidade que não seja `vitimas` ou `ocorrencias` aborta (`ErroAgregacao`), em vez de ser pulada. O comando converte `ErroAgregacao` em `CommandError`, o que desfaz a transação.

### 4.9 Gravação idempotente

```python
RegistroAnual.objects.bulk_create(
    objetos,
    batch_size=2000,
    update_conflicts=True,
    unique_fields=["estado", "regiao", "indicador", "recorte", "unidade", "ano"],
    update_fields=["valor", "taxa_publicada", "situacao", "observacao", "fonte", "origem", "metodo"],
)
```

- `origem` precisa de `max_length` suficiente para a soma de até 9 células (Nordeste), ex.: `T14!M13+M14+M15+…`. Use 200.

- O `ON CONFLICT` usa a constraint `NULLS NOT DISTINCT`, de modo que registros sem recorte ou de região atualizam em vez de duplicar. **Teste obrigatório:** importar duas vezes a fixture e comparar contagem e o conjunto de `id`.
- Registros da carga anterior ausentes na atual não são apagados: entram no relatório como "órfãos".

---

## 5. Relatório de validação (RF12)

Gerado em `dados/relatorios/validacao-<versao>.csv` (uma linha por apontamento) e `validacao-<versao>.md` (resumo com totais por tabela).

Todas as comparações são feitas em **precisão total, sem arredondar nenhum lado**, com tolerância absoluta `|calculado − publicado| ≤ 1e-6` (`TOLERANCIA = Decimal("1e-6")` em `validacao.py`, ADR 0004). A diferença real hoje é da ordem de 1e-14, e o arredondamento de `taxa_publicada` a 12 casas acrescenta no máximo 5e-13.

| Verificação | Regra | Severidade |
| :--- | :--- | :--- |
| Taxa calculada × publicada | Base 100 mil hab., anos 2024 e 2025, vítimas e ocorrências: `valor / pop × 100000` contra `taxa_publicada` | divergência acima da tolerância |
| Variação calculada × publicada | Variação **da taxa** (a mesma de `variacao.taxa_pct` na API) contra a coluna "Variação (%)". A coluna do FBSP não é a variação dos absolutos | divergência acima da tolerância |
| Participação calculada × proporção publicada | T09 (MDIP ÷ MVI × 100) e T21 (feminicídio ÷ homicídio de mulheres × 100), mesma regra da `participacao` da API | divergência acima da tolerância |
| Conferência T01 × T02 | MVI 2024–2025, valor e taxa | divergência |
| Conferência T09 × T02 e T08 | Absolutos de MVI e de MDIP (total), 2024–2025 | divergência |
| Base da taxa × cabeçalho | Rótulo do grupo, ou nota marcada no grupo, contém a `base_taxa` (seção 4.3) | erro (aborta) |
| Soma dos recortes × total (T08) | Informativo | informação |
| Soma das UFs × Brasil | Soma das UFs que informaram contra o total publicado (seção 4.8), por unidade | erro (aborta) |
| Soma das UFs × região publicada | T02, todos os anos (seção 4.8) | erro (aborta) |
| Regiões calculadas | Quantidade por tabela e unidade e quantas ficaram `nao_disponivel` | informação |
| Contagem por situação | `informado`, `inexistente`, `nao_disponivel` por tabela | informação |
| Célula vazia | Ocorrência de vazio em área de dados | aviso |
| Órfãos | Chaves da carga anterior ausentes na atual | aviso |
| Variação ou proporção publicada como "-" ou "..." | Não há número a comparar. Só é apontada quando o sistema calcula um número onde a planilha não publicou nenhum (ex.: T15, roubo a instituição financeira que caiu a zero: −100% calculado, "..." publicado); "-" com variação calculada nula (base zero) passa sem apontamento | informação |
| Marca de nota do IBGE | Ex.: `(1)` em PR e SC em 2025, com o texto da nota | informação |

Colunas do CSV: `tabela, origem, indicador, localidade, recorte, unidade, ano, verificacao, esperado, obtido, diferenca, severidade`. `esperado`, `obtido` e `diferenca` em precisão total.

---

## 6. Testes

- `tests/fixtures/planilhas/`: planilhas reduzidas geradas por `tests/fixtures/gerar_planilhas.py` a partir das reais, com manifesto de hashes próprio. Do FBSP, só as abas T01, T02, T03, T08, T09, T15 e T21, mas com **todas as linhas**: a agregação regional exige todas as UFs de cada região, e o leitor confere 28 ou 33 localidades. Do IBGE, só a aba `BRASIL_E_UFs`. Com elas, a importação gera 1.134 lidos + 120 calculados = 1.254 registros e 66 populações.
- Unitários: `normalizar_celula`, `normalizar_taxa`, `separar_marcas`, `resolver_localidade`, o leitor do FBSP sobre uma aba sintética (âncora, colunas órfãs e ignoradas, base da taxa, notas, células inválidas e vazias, contagens), leitura do IBGE, `agregacao.agregar`, relatório, referências e constraints do banco.
- Integração (`tests/importacao/test_processo.py`, `test_comando.py`): importação completa sobre as fixtures; idempotência (duas execuções, mesmos `id`s); `--somente-validar` sem gravar nada; rollback (célula inválida → nada gravado, carga `falhou`); agregado publicado divergente → aborta; taxa divergente plantada → relatório e `--estrito`; hash divergente; órfãos; ids de fontes e recortes num banco limpo.
- Contra a planilha real (`@pytest.mark.planilha_real`): toda âncora é encontrada na linha 5, toda coluna de taxa passa na conferência da base, nenhuma coluna órfã, 1.750 registros lidos + 230 regionais calculados (24 nulos) = 1.980, e 66 populações; nenhuma divergência entre agregados publicados e a soma das UFs; e nenhuma divergência acima de 1e-6 no relatório (taxas de vítimas e ocorrências, variação da taxa, T09 e proporção da T21 — conferido na planilha versionada).
