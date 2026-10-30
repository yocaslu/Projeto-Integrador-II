# CLAUDE.md

Plataforma de análise do **20º Anuário Brasileiro de Segurança Pública (FBSP, 2026)**: banco relacional (PostgreSQL 18) → API REST somente leitura (Django + DRF) → dashboard (React). Licença AGPL-3.0.

**Fonte da verdade:**
- **API:** `docs/contrato-api.md` (transcrição detalhada do Roteiro, com as decisões do ADR 0003). Prevalece sobre o resumo deste arquivo e sobre o texto do Roteiro.
- **Importação:** `docs/importacao.md`.
- **Modelagem:** `docs/modelagem.md` (transcrição do Roteiro com os ajustes dos ADRs). Prevalece sobre o texto do Roteiro.
- **Requisitos:** o documento "Roteiro" do projeto (resumo na seção "Requisitos" abaixo).

Se o código divergir desses documentos, pare e pergunte antes de "corrigir" qualquer um dos lados.

---

## Escopo atual

**A fase do backend está concluída**: modelos, importação da planilha, API `/api/v1/` com todos os recursos do contrato (inclusive CSV e cache), esquema OpenAPI e teste de desempenho do RNF02. Mudanças no backend seguem as regras abaixo. **A fase atual é o frontend.**

- Feito no frontend: filtros (indicador, região, UF, ano do ranking), cartões da UF (taxa, variação, posição, número absoluto), gráfico de evolução UF × região × Brasil (`/comparacao/`), comparação entre estados em barras (`/ranking/`), tabelas de dados acessíveis e links de CSV; testes Jest e Playwright + axe com o painel carregado.
- Mapa por UF (RF06): Leaflet sem camada de fundo, coroplético em 5 classes por quantis, com os dados de `/ranking/` ligados à malha pelo código IBGE (`codarea`). A malha fica em `frontend/public/malhas/ufs.json`, gerada por `npm run malha` a partir da API de malhas do IBGE (`frontend/public/README.md`). No Jest, `react-leaflet` é trocado por `src/testes/reactLeafletFalso.jsx` (`moduleNameMapper`).
- O frontend só consome a API; nenhum cálculo de taxa, variação ou ranking é refeito no cliente.
- Ordem de entrega (concluída): `localidades` e `catalogo` → `importacao` (comando + relatório de validação) → `registros` (consultas de taxa, variação, ranking, comparação) → `api` (endpoints, filtros, erros, CSV, cache) → documentação OpenAPI.
- Ordem dentro da app `api` (concluída; cada passo com os testes da seção 8 do contrato que lhe cabem):
  1. `parametros.py` (regras comuns da seção 2 do contrato) e `campos.py` (decimais da seção 1.2);
  2. catálogos: `/regioes/`, `/estados/`, `/fontes/`, `/indicadores/`, `/recortes/`;
  3. `queries.py`: anotação de taxa, variação e participação no SQL (precisão total, sempre na mesma unidade), ordem canônica de localidades;
  4. `/registros/` (filtros, regra de nível, ordenação, paginação) e `/populacao/`;
  5. `/ranking/` e `/comparacao/`; 6. `/metadados/`;
  7. CSV (negociação, colunas, limite, streaming); 8. cache (ETag, `Vary`, 304); 9. `openapi.yaml`.
- Requisitos em foco: RF01, RF02, RF05, RF07–RF13, RNF02, RNF05–RNF12. Os de interface (RF03, RF04, RF06, RNF01, RNF03) ficam para a fase do frontend, mas o contrato da API já precisa atendê-los.

---

## Comandos

Rodam a partir da raiz do repositório. Serviços do Compose: `db`, `backend` e `frontend` (painel em `http://localhost:5173`).

**Primeira vez**
```bash
cp .env.example .env
docker compose up -d --build db backend
docker compose exec backend uv run python manage.py migrate
docker compose exec backend uv run python manage.py importar_anuario
```

**Dia a dia**

| Tarefa | Comando |
| :--- | :--- |
| Subir o ambiente | `docker compose up -d db backend` |
| Derrubar | `docker compose down` (`-v` apaga o banco) |
| Logs | `docker compose logs -f backend` |
| Shell no container | `docker compose exec backend bash` |
| Criar migrações | `docker compose exec backend uv run python manage.py makemigrations` |
| Aplicar migrações | `docker compose exec backend uv run python manage.py migrate` |
| Verificar migração pendente | `docker compose exec backend uv run python manage.py makemigrations --check --dry-run` |
| Importar os dados | `docker compose exec backend uv run python manage.py importar_anuario` |
| Inspecionar a planilha (nova edição) | `docker compose exec backend uv run python manage.py inspecionar_planilha T03 T08` |
| Testes com cobertura (≥ 75%) | `docker compose exec backend uv run pytest` |
| Um teste específico | `docker compose exec backend uv run pytest tests/importacao/test_normalizacao.py -k inexistente` |
| Importação da planilha real | `docker compose exec backend uv run pytest -m planilha_real --no-cov` |
| Desempenho (RNF02) | `docker compose exec backend uv run pytest -m desempenho --no-cov` |
| Lint e formatação (verificar) | `docker compose exec backend uv run ruff check . && docker compose exec backend uv run ruff format --check .` |
| Lint e formatação (corrigir) | `docker compose exec backend uv run ruff check --fix . && docker compose exec backend uv run ruff format .` |
| Gerar o esquema OpenAPI versionado | `docker compose exec -T backend uv run python manage.py spectacular --validate --fail-on-warn > docs/api/openapi.yaml` |
| Adicionar dependência | `cd backend && uv add <pacote>==<versão>` (ou `uv add --dev`) |

Notas:
- `uv run pytest` já aplica `--cov` e `fail_under = 75` pelo `pyproject.toml`; não repita as opções. Os testes `planilha_real` e `desempenho` ficam fora da execução padrão e rodam em passos próprios do CI.
- `importar_anuario` lê `--dados` (padrão `DADOS_BRUTOS_DIR=/dados/brutos`) e grava o relatório em `--relatorio` (padrão `DADOS_RELATORIOS_DIR=/dados/relatorios`). `./dados` é montado em `/dados` no container. Os hashes são conferidos contra `dados/README.md` (outro arquivo com `--manifesto`). `--somente-validar` lê, confere e gera o relatório sem gravar nada; `--estrito` termina com erro se o relatório tiver divergência. Antes de ajustar `mapeamento.py` para uma nova edição da planilha, rode `inspecionar_planilha [ABA ...]`.
- Sem Docker, os mesmos comandos funcionam dentro de `backend/` com `uv run ...`, apontando `POSTGRES_HOST=localhost`.

Sequência completa em ambiente limpo: subir → `migrate` → `importar_anuario` → `pytest`.

URLs locais: API em `http://localhost:8000/api/v1/`, Swagger em `/api/v1/docs/`, ReDoc em `/api/v1/redoc/`, esquema em `/api/v1/schema/`.

---

## Decisões do projeto

### Stack (versões fixadas — não atualize sem ADR)
Python 3.14 (série; qualquer 3.14.x, ADR 0006) · Django 6.1.2 · DRF 3.18.3 · django-filter 26.2 · drf-spectacular 0.30.0 · psycopg 3.3.6 · pandas 3.0.6 · openpyxl 3.1.5 · odfpy 1.4.1 · PostgreSQL 18 · uv 0.13.5 (`uv.lock` versionado) · Ruff 0.17.2 · pytest 9.1.1 + pytest-django 4.14.0 + pytest-cov 7.1.0 · Gunicorn 26.2.0 (ADR 0006) · Docker + Traefik em VMs Ubuntu Server 26.04 (Proxmox VE) · GitHub Actions. Frontend (fase seguinte): React, Recharts, Leaflet, Jest, Playwright + axe-core.

### Arquitetura
- REST (Fielding, 2000): cliente e servidor desacoplados; a API é um produto reutilizável por terceiros, não um detalhe do dashboard.
- Apps do backend organizadas por **domínio**: `localidades`, `catalogo`, `registros`, `importacao`, `api`.
- `importacao` é a **única** app que grava no banco; `api` apenas lê (RNF06).
- Cálculos (taxa, variação, ranking com empates, comparação) ficam em `apps/registros/queries.py`, fora das views, para serem reutilizados por `/registros/`, `/ranking/` e `/comparacao/` e testados sem HTTP.
- Testes rodam no PostgreSQL (não SQLite), porque o modelo usa `NULLS NOT DISTINCT`.

### Indicadores do escopo
MVI (indicador-síntese), letalidade policial (mortes decorrentes de intervenção policial), feminicídio, roubo (total e subtipos) e furto (só subtipos: veículo e celular; o Anuário não publica total de furtos). Homicídio doloso, latrocínio e lesão corporal seguida de morte são importados em **vítimas e ocorrências** (T03–T05); os demais, só na sua unidade padrão. Proporções (T09, T21) são **calculadas pela API** (`participacao`), não importadas. Perfis de vítimas (sexo, raça/cor, faixa etária) estão **fora do escopo** (ADR 0004).

### Modelo de dados (resumo)
- `REGIOES` (5 regiões + Brasil, `tipo` = `regiao`|`pais`); `ESTADOS` (27 UFs, cada uma em uma região).
- `REGISTROS_ANUAIS` é a tabela de fatos: um valor por (localidade, indicador, recorte, unidade, ano), com fonte.
- Localidade = `estado_id` **ou** `regiao_id`, exatamente um (`CheckConstraint`).
- Unicidade em (estado, regiao, indicador, recorte, unidade, ano) com `UniqueConstraint(..., nulls_distinct=False)`.
- `INDICADORES` em hierarquia (`indicador_pai`), que significa "contido em", nunca "soma de": MVI → homicídio doloso (→ homicídio de mulheres → feminicídio), latrocínio, lesão corporal seguida de morte, morte decorrente de intervenção policial; Roubo → veículo, celular, transeunte, residência, estabelecimento comercial, instituição financeira, carga; Furto (agrupador sem registros) → veículo, celular.
- Indicadores-pai e o total do Brasil são **importados**, nunca somados. As regiões são importadas quando o FBSP as publica (só MVI, T02); nos demais casos são **calculadas na importação** como soma das UFs (`metodo = soma_ufs`). Se alguma UF da região estiver "...", a região fica nula (`nao_disponivel`). Detalhes em `docs/importacao.md`, seção 4.8.
- Características dos agentes são **recortes** (`RECORTES` + `RECORTE_ITENS`, pares dimensão/valor; dimensões `corporacao` e `situacao_policial`, ex.: corporação = Polícia Militar + situação = em serviço). Registro sem recorte = total.
- `situacao`: `informado` | `inexistente` (“-” → valor 0) | `nao_disponivel` (“...” → valor nulo). Notas do FBSP vão em `observacao`.
- `unidade` (`vitimas` | `ocorrencias`) fica no **registro**; `INDICADORES` guarda `unidade_padrao` e `base_taxa` (100 mil habitantes; 100 mil mulheres; 100 mil veículos; 100 instituições). A base vale para as duas unidades.
- Taxa por 100 mil habitantes é **calculada** a partir de `POPULACAO` (IBGE 2024 e 2025, as mesmas estimativas usadas pelo FBSP); nos demais casos (outras bases e série MVI 2012–2023) usa-se `taxa_publicada`. A variação percentual é calculada na consulta e nunca armazenada. A população de 2012 a 2023 já foi decidida e aguarda implementação (pendência 12).

Ajustes ao modelo do roteiro, implementados nas migrações iniciais (ADR 0007, que também registra as decisões da implementação):
1. `INDICADORES.slug` (único) — exigido pelo contrato da API.
2. `ESTADOS.codigo_ibge` e `REGIOES.codigo_ibge` — chave estável para a malha do mapa e para cruzamentos futuros. `CharField(max_length=2)` com os códigos reais do IBGE: UFs `11`…`53` (únicos), regiões `1`…`5`, Brasil `1`; em `REGIOES`, unicidade por (`tipo`, `codigo_ibge`). Siglas em `REGIOES`: `BR`, `N`, `NE`, `SE`, `S`, `CO`.
3. `RECORTES.chave` (única, pares ordenados `dimensao=valor;...`) — torna a criação de recortes idempotente.
4. `REGISTROS_ANUAIS.origem` (ex.: `T08!D15`) — rastreabilidade de cada valor até a célula da planilha; quando `metodo = soma_ufs`, lista as células somadas (`T03!C19+C24+C30+C36`).
5. Nova entidade `CARGAS` (versao, sha256 de cada arquivo, iniciada_em, concluida_em, status, total_registros) — alimenta `/metadados/` e o ETag.
6. `POPULACAO` recebe a mesma CHECK de localidade e unicidade (localidade, ano) `NULLS NOT DISTINCT`.
7. `taxa_publicada` guarda a taxa publicada **arredondada a 12 casas**: `DecimalField(max_digits=24, decimal_places=12)`. A planilha traz até 17 dígitos significativos (até 18 casas), que são a representação em ponto flutuante do Excel, não precisão do FBSP; o erro de até 5e-13 é irrelevante para a análise, mas o valor gravado não reproduz a célula dígito a dígito (ADR 0003). O arredondamento é feito na importação, em `normalizacao.py`, com `Decimal(str(v)).quantize(Decimal("1e-12"), ROUND_HALF_UP)`, para que a linha em memória seja igual à gravada. `valor`: `DecimalField(max_digits=18, decimal_places=4)`.
8. `REGISTROS_ANUAIS.metodo` (`publicado` | `soma_ufs`, padrão `publicado`) — distingue o valor lido da planilha do agregado regional calculado pelo projeto; exposto na API (RF11). `origem` com `max_length=200`, porque a linha regional lista as células somadas.
9. `INDICADORES.ordem` (inteiro único, pré-ordem da hierarquia) — ordena indicadores na API; valores em `docs/importacao.md`, seção 2 (ADR 0003).
10. `REGISTROS_ANUAIS.unidade` (`vitimas` | `ocorrencias`), na chave única (ADR 0004) — o mesmo indicador tem vítimas e ocorrências (T03–T05).
11. `INDICADORES.unidade` passa a `INDICADORES.unidade_padrao` — a unidade que a API usa quando o cliente não pede outra (ADR 0004). A unidade `percentual` deixa de existir.
12. `INDICADORES.fonte_taxa` (FK anulável para `FONTES`, `PROTECT`) — fonte do denominador da taxa, de onde a API tira `taxa.fonte`; nula se e somente se `base_taxa` é nula (`CheckConstraint`). Habitantes → `ibge-estimativas`; mulheres → `ibge-projecoes`; veículos → `senatran-frota`; instituições → `bcb-instituicoes` (ADR 0005).
13. `FONTES.slug` (único) — catálogo fixo em `catalogo/referencia.py`, criado primeiro e sempre na mesma ordem com `update_or_create(slug=…)`, para ids estáveis: 1 `secretarias-seguranca`, 2 `ibge-estimativas`, 3 `ibge-projecoes`, 4 `senatran-frota`, 5 `bcb-instituicoes` (ADR 0005; contrato, 4.5).

### Contrato da API (resumo)

Resumo para orientação. **O que vale é `docs/contrato-api.md`**: leia a seção do recurso antes de escrever o serializer, o filtro ou o teste dele, e não decida no código nada que o contrato já define.

**Geral**
- Prefixo `/api/v1/`, `URLPathVersioning`. Mudança incompatível → `/api/v2/`; a v1 continua no ar. Acrescentar campo, parâmetro opcional ou recurso é compatível.
- Só `GET`, `HEAD`, `OPTIONS`; o resto → 405.
- Nomes em português, `snake_case`, iguais aos atributos do modelo. UF e região por sigla (aceitas sem diferença de caixa, devolvidas em maiúsculas); indicador por slug.
- Localidade = par (`nivel`, `codigo`): `{"nivel", "codigo", "codigo_ibge", "nome"}`. Siglas `BR`, `N`, `NE`, `SE`, `S`, `CO` e as 27 UFs. Ordem canônica: Brasil, regiões por `codigo_ibge`, UFs por sigla.
- Campo do contrato nunca é omitido: ausência = `null` (CSV: campo vazio). `taxa` e `variacao` são objetos sempre presentes.

**Formatos de resposta**
- Catálogos (`/regioes/`, `/estados/`, `/indicadores/`, `/recortes/`, `/fontes/`): array JSON na raiz, sem paginação.
- `/registros/` e `/populacao/`: paginados (`pagina` padrão 1, `tamanho` padrão 100, máx. 1000, acima → 400), envelope `count`/`next`/`previous`/`results`.
- `/ranking/`, `/comparacao/`, `/metadados/`: objeto, com os parâmetros efetivos (inclusive padrões resolvidos) ecoados.
- Registro: `id`, `ano`, `localidade`, `indicador` (`slug`, `nome`), `recorte` (`null` | `id`, `rotulo`, `itens`), `unidade`, `valor`, `situacao`, `metodo`, `taxa` (`valor`, `base`, `origem`, `fonte` = `indicador.fonte_taxa`; `origem` e `fonte` nulas sempre que não há taxa, ADR 0008), `taxa_publicada`, `variacao` (`ano_referencia` = ano − 1, `valor_pct`, `taxa_pct` = variação da taxa, a mesma do FBSP), `participacao` (`referencia` {`tipo`, `indicador`} | `null`, `valor_pct`), `fonte`, `observacao`.
- `participacao`: sem recorte, valor ÷ indicador-pai × 100 (`indicador_pai`); com recorte, valor ÷ total do mesmo indicador × 100 (`total_do_indicador`); mesma localidade, ano e unidade; nula em raízes e filhos de agrupador. Substitui as proporções da T09 e da T21. Nunca somar participações.

**Decimais** (texto, `COERCE_DECIMAL_TO_STRING = True`)
- `valor` de vítimas/ocorrências e população: inteiro (`"5800"`). `taxa.valor`, `valor_pct`, `taxa_pct`, `participacao.valor_pct`: 2 casas fixas (`"40.94"`, `"-3.10"`). `taxa_publicada`: precisão guardada, sem zeros à direita nem notação exponencial.
- Arredondar **só** na serialização (`apps/api/v1/campos.py`), meio para longe do zero (`ROUND_HALF_UP`, igual ao `round()` do PostgreSQL). `queries.py` devolve precisão total.
- Ordenação por taxa e ranking usam o valor **arredondado** (a API classifica pelo que mostra).

**`/registros/`**
- Parâmetros: `nivel`, `uf`, `regiao`, `indicador`, `incluir_subtipos`, `ano` | `ano_min`/`ano_max`, `unidade` (`padrao` padrão | `todas` | lista de `vitimas`, `ocorrencias`), `recorte` (`total` padrão | `todos` | ids), `situacao`, `ordenar`. Listas por vírgula.
- `unidade=padrao` = a `unidade_padrao` de cada indicador: vítimas e ocorrências do mesmo crime nunca se misturam por omissão. `indicador` informado sem registros na unidade pedida → 400.
- Nível: sem `nivel`, `uf` ou `regiao` → só as UFs. `uf` implica `nivel=uf`. `regiao` exige `nivel` explícito (`uf` → UFs da região; `regiao` → agregado). Mistura de níveis só por lista explícita (`nivel=pais,regiao,uf`), e então sem `uf`/`regiao`. `uf` + `regiao`, `nivel=regiao&uf=SP`, `nivel=pais&regiao=…` → 400. Tabela completa: contrato, 4.7.2.
- `incluir_subtipos=true` exige `indicador` e traz todos os descendentes. `indicador=furto` sem ele → 400.
- `ordenar`: `ano`, `indicador` (por `ordem`), `localidade` (canônica), `recorte`, `unidade`, `valor`, `taxa`, `variacao_valor`, `variacao_taxa`, `participacao`. Padrão `indicador, localidade, recorte, unidade, ano`; desempate final por `id`; nulos ao final nas duas direções; taxa, variação e participação anotadas e ordenadas no SQL.

**`/ranking/`**: `indicador` (um, obrigatório), `ano` (um; padrão = último ano com dados do indicador), `criterio` (`taxa` padrão | `valor` | `participacao`), `unidade` (uma; padrão = `unidade_padrao`), `recorte` (`total` padrão | um id). Só as 27 UFs, decrescente, empates (1, 2, 2, 4), nulos ao final com `posicao: null`. Itens sem `taxa_publicada` (fica só em `/registros/`).

**`/comparacao/`**: `uf` (uma, obrigatória), `indicador` (um, obrigatório), `ano_min`/`ano_max` (padrão = anos do indicador), `unidade` (uma; padrão = `unidade_padrao`), `recorte` (`total` padrão | um id). `series` = [UF, região da UF, Brasil], cada uma com `pontos` por ano, os mesmos anos nas três. Pontos sem `taxa_publicada`.

**`/metadados/`**: `carga`, `anos` (min/max), `niveis`, `unidades`, `situacoes`, `metodos`, `fontes` e a árvore aninhada de `indicadores` (cada nó com os mesmos campos de um item de `/indicadores/`, e `subtipos` com os objetos dos filhos). `/indicadores/` traz `unidade_padrao` e `unidades` em vez de `unidade`.

**Parâmetros, CSV e erros**
- Parâmetro desconhecido, repetido (`uf=SP&uf=RJ`) ou vazio → 400. Valor inexistente em parâmetro de consulta (`uf=XX`) → 400; 404 só para caminho (`/estados/XX/`).
- Reservados: `formato` (`json` | `csv`) em todos os recursos; `pagina`/`tamanho` só em `/registros/` e `/populacao/` e só em JSON.
- CSV em `/registros/`, `/populacao/`, `/ranking/`, `/comparacao/`; nos demais, `formato=csv` ou `Accept: text/csv` → 406. `formato` prevalece sobre `Accept`; formato desconhecido → 406 (não o 404 do DRF; `URL_FORMAT_OVERRIDE = "formato"`).
- CSV: RFC 4180, UTF-8 sem BOM, `\r\n`, cabeçalho sempre, nulo = vazio, mesmos arredondamentos do JSON, streaming, máx. 50 mil linhas (acima → 400), achatamento por `_` (`taxa_valor`), `fonte`/`taxa_fonte` só com o nome. **Colunas e ordem são contrato** (contrato, 5.3).
- Erros em Problem Details (RFC 9457), `application/problem+json`, com lista `erros` em validações (já em `apps/api/erros.py`), sempre em JSON, mesmo quando o CSV foi pedido.
- Cache: `Cache-Control: public, max-age=86400`, `ETag: W/"<versao>-<json|csv>"`, `Vary: Accept`, 304 com `If-None-Match`. `versao` = carga concluída com o maior `concluida_em`.
- Sem nenhuma carga concluída: 503 em Problem Details em todo recurso de `/api/v1/` (menos `schema`, `docs`, `redoc`), com `Cache-Control: no-store` e sem `ETag` (contrato, 7.1).

### Requisitos (referência rápida)

| Código | Resumo |
| :--- | :--- |
| RF01 | Importar e normalizar planilha do FBSP e estimativas do IBGE |
| RF02 | API por estado, região, ano, indicador, subtipo, unidade (vítimas/ocorrências) e recorte (características dos agentes) |
| RF05 | Taxas por 100 mil hab. (IBGE) e variação percentual |
| RF07 | Exportação CSV |
| RF08 | Documentação OpenAPI interativa |
| RF09 | Endpoint de metadados |
| RF10 | Ranking das UFs |
| RF11 | Situação do dado e notas metodológicas junto a cada valor |
| RF12 | Importação idempotente + relatório de validação das taxas |
| RF13 | Comparação UF × região × Brasil |
| RNF02 | p95 < 500 ms em consultas filtradas por UF, ano e indicador (teste automatizado; método no ADR 0005) |
| RNF05 | Cobertura ≥ 75% no CI |
| RNF06 | API somente leitura; carga só por comando administrativo |
| RNF07 | Configuração por variáveis de ambiente, sem credenciais no repositório |
| RNF08 | Ambiente reproduzível com Docker Compose |
| RNF09 | Lint e formatação verificados no CI |
| RNF10 | Valores e taxas em NUMERIC |
| RNF11 | Respostas em cache |
| RNF12 | Fontes (FBSP e IBGE) indicadas na API e nos CSVs |
| RNF13 | AGPL-3.0, com link para o repositório na interface |

---

## Estrutura do repositório

Árvore atual.

```
projeto-integrador-ii/
├── CLAUDE.md
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                     # Ruff, migrações, pytest, planilha real, diff do openapi.yaml, desempenho
│   │   ├── deploy.yml
│   │   └── release.yml                # tag vX.Y.Z: confere versões, roda o CI, publica imagens e o release (ADR 0010)
│   └── pull_request_template.md       # checklist da Definição de pronto
├── backend/
│   ├── pyproject.toml · Dockerfile · manage.py · .python-version
│   ├── uv.lock                        # versionado; o build e o CI usam --locked
│   ├── config/settings/               # base.py, dev.py, test.py, prod.py
│   ├── apps/
│   │   ├── localidades/               # Regiao, Estado, Populacao
│   │   │   └── referencia.py          # 5 regiões + Brasil + 27 UFs (sigla, nome, código IBGE, aliases)
│   │   ├── catalogo/                  # Fonte, Indicador, Recorte, RecorteItem
│   │   │   └── referencia.py          # fontes (slug, ordem fixa) e hierarquia de indicadores (slug, pai, unidade_padrao, base_taxa, fonte_taxa)
│   │   ├── registros/                 # RegistroAnual
│   │   │   ├── escolhas.py            # Situacao, Metodo, Unidade (TextChoices usados pelos modelos e pela importação)
│   │   │   └── queries.py             # anotar_registros (taxa, variação, participação por subconsulta), ordenacao, ordem canônica, ranking, comparacao
│   │   ├── importacao/
│   │   │   ├── models.py              # Carga
│   │   │   ├── mapeamento.py          # especificação declarativa das tabelas (T01–T21) e contagem esperada
│   │   │   ├── processo.py            # fluxo completo da importação (o comando só trata opções)
│   │   │   ├── leitores/              # fbsp.py (openpyxl), ibge.py (pandas + odfpy)
│   │   │   ├── normalizacao.py        # “-”, “...”, Decimal, taxa a 12 casas, localidades
│   │   │   ├── linhas.py              # Chave (com `unidade`), Linha, Localidade (nível + sigla), Metodo, Unidade
│   │   │   ├── agregacao.py           # regiões = soma das UFs; confere Brasil e T02; somável pela unidade da chave
│   │   │   ├── gravacao.py            # referências, população e upsert idempotente; órfãos
│   │   │   ├── validacao.py           # relatório (sem arredondar, tolerância 1e-6): taxa, variação da taxa, T01, T09/T21
│   │   │   └── management/commands/
│   │   │       ├── importar_anuario.py
│   │   │       └── inspecionar_planilha.py # lista abas, âncoras e caminhos de cabeçalho
│   │   └── api/
│   │       ├── v1/                    # urls, views, serializers, filtros
│   │       │   ├── parametros.py      # LeitorParametros: desconhecido/repetido/vazio → 400, listas, anos, nível × uf × região, ordenar
│   │       │   └── campos.py          # campos decimais (inteiro, 2 casas, precisão guardada) e objetos localidade, taxa, variação, participação
│   │       └── erros.py · negociacao.py · paginacao.py (paginar: 400 além da última página) · renderizadores.py (CSV: colunas da 5.3, achatamento, streaming, limite) · cache.py (Cache-Control, ETag por carga e formato, 304)
│   └── tests/                         # espelha apps/: importacao/, registros/, api/, desempenho/ (RNF02, ADR 0005)
│       ├── localidades/ · catalogo/
│       ├── conftest.py
│       └── fixtures/                  # planilhas reduzidas (gerar_planilhas.py; abas selecionadas, todas as linhas)
├── frontend/                          # React + Recharts: paginas/Painel.jsx, componentes/, hooks/, utils/ (cores e formatação)
├── e2e/                               # Playwright + axe-core contra o ambiente com dados importados
├── dados/
│   ├── README.md                      # origem e SHA-256 de cada arquivo
│   ├── brutos/                        # anuario-2026.xlsx, POP2024_20241230.ods, POP2025_20260828.ods
│   └── relatorios/                    # gerados pela importação (fora do Git)
├── infra/                             # compose.prod.yml, traefik/
├── docs/
│   ├── importacao.md                  # mapeamento da planilha e algoritmo de extração
│   ├── contrato-api.md                # contrato completo da API v1 (fonte da verdade)
│   ├── modelagem.md                   # modelagem de dados (fonte da verdade; transcrição do roteiro com os ADRs)
│   ├── api/openapi.yaml               # esquema gerado e versionado (diff verificado no CI)
│   └── adr/                           # 0001 a 0010 (0007: modelo e importação; 0008: cálculos no SQL, JIT e índice; 0009: variação do Brasil em recortes; 0010: versões e releases)
├── docker-compose.yml · .env.example · .editorconfig · .gitignore · LICENSE · README.md
```

Motivos da organização:
- **`referencia.py` em `localidades` e `catalogo`**: dados de referência fixos vivem no código, revisados em PR, e são carregados pelo `importar_anuario` antes dos fatos.
- **`importacao` em leitura → normalização → gravação → validação**: cada etapa testável isoladamente; o mapeamento é dado, não lógica espalhada.
- **`inspecionar_planilha`**: a planilha muda de layout entre edições; o comando mostra os caminhos de cabeçalho antes de alguém ajustar `mapeamento.py`.
- **`docs/api/openapi.yaml` versionado**: toda mudança de contrato fica visível no diff do PR e permite exigir "OpenAPI atualizado" na Definição de pronto.

---

## Importação da planilha

Especificação completa (tabelas, colunas, regras e pseudocódigo) em **`docs/importacao.md`**. Leia antes de mexer em `apps/importacao/`.

Resumo:
- **Lidas:** T02 (MVI 2012–2025), T03 (homicídio doloso), T04 (latrocínio), T05 (lesão corporal seguida de morte) — T03–T05 em vítimas e ocorrências, T08 (MDIP por corporação e situação), T11 (roubo/furto de veículo), T12 (roubo/furto de celular), T14 (roubo a estabelecimento comercial, residência, transeunte), T15 (roubo a instituição financeira, de carga e total), T21 (homicídio de mulheres e feminicídio).
- **Só conferência:** T01 (MVI 2024–2025; idêntica a T02), T09 (MVI, MDIP e proporção MDIP/MVI) e a coluna de proporção da T21; as proporções são comparadas à `participacao` calculada.
- **Ignoradas:** painéis (P), gráficos (G), quadros (Q) e as demais tabelas.
- **População:** aba `BRASIL_E_UFs` dos dois `.ods` do IBGE, já com totais de regiões e Brasil.
- **Volume esperado:** 1.980 registros (1.750 lidos + 230 regionais calculados, dos quais 24 nulos) e 66 linhas de população. Contagem diferente é falha da importação.

Algoritmo:
1. Conferir o SHA-256 dos arquivos contra `dados/README.md`; se divergir, abortar.
2. Abrir uma `Carga` e iniciar `transaction.atomic()`.
3. Carregar as referências com `update_or_create`.
4. Ler a população e gravar `POPULACAO`.
5. Para cada tabela de `mapeamento.py`:
   1. localizar a âncora;
   2. expandir as células mescladas;
   3. montar o caminho de cabeçalho de cada coluna;
   4. ler as linhas até "Fonte:", pulando as linhas em branco;
   5. resolver a localidade e normalizar as células.
6. Agregar as regiões (`agregacao.agregar`): conferir Brasil e regiões publicadas contra a soma das UFs (diverge → aborta) e calcular as regiões que faltam.
7. Gravar com upsert (`bulk_create(update_conflicts=True, ...)`), sem apagar nem duplicar.
8. Gerar o relatório em `dados/relatorios/` e fechar a `Carga`.

---

## Regras invariáveis

Valem para qualquer mudança. Se uma tarefa exigir quebrar uma delas, pare e pergunte.

**Dados e importação**
1. Nunca editar arquivos em `dados/brutos/`. Nova versão de planilha = novo arquivo + novo hash em `dados/README.md`, em commit próprio.
2. O banco só é escrito pelo comando `importar_anuario` (e pelas migrações). Nada de endpoints de escrita, admin com escrita, fixtures em produção ou SQL manual.
3. A importação é idempotente: rodar duas vezes não muda contagem nem `id` de nenhum registro. Há teste para isso.
4. Indicadores-pai e o total do Brasil são **importados**, nunca somados a partir dos subtipos ou das UFs. Regiões: importadas quando publicadas (T02); nos demais casos, calculadas só em `agregacao.py`, como soma das UFs da região, apenas para unidade absoluta (vítimas, ocorrências), no mesmo indicador, recorte, unidade e ano, com `metodo = soma_ufs`. Se alguma UF da região estiver "...", a região fica `NULL`/`nao_disponivel`, nunca soma parcial. Taxas nunca são somadas nem tiradas em média. Agregado publicado que divirja da soma das UFs que informaram aborta a importação.
5. Não existe total de furtos. O indicador `furto` não tem registros próprios; nunca calcule nem exiba um total. Os blocos "Roubo e Furto" das tabelas T11 e T12 não são importados.
6. “-” → `valor = 0`, `situacao = inexistente`. “...” → `valor = NULL`, `situacao = nao_disponivel`. Célula vazia → `nao_disponivel` com aviso no relatório. Qualquer outro texto aborta a importação com a célula de origem na mensagem.
7. Localidade não reconhecida, coluna de cabeçalho não resolvida ou contagem diferente da esperada abortam a importação. Nunca pular linha em silêncio.
8. Cada (indicador, localidade, recorte, ano) tem **uma** tabela dona em `mapeamento.py`; outra tabela com o mesmo dado só entra como conferência no relatório.
9. Perfis de vítimas (sexo, raça/cor, faixa etária) estão fora do escopo; as únicas dimensões de recorte são `corporacao` e `situacao_policial`. Proporções publicadas (T09, T21) não são importadas: são `participacao`, calculada na consulta.

**Banco e cálculos**
10. Valores, taxas e populações usam `DecimalField` (NUMERIC). `float` é proibido em modelos, cálculos e serializers; converter célula com `Decimal(str(v))`.
11. Taxa calculada só quando a base é 100 mil habitantes e há população do IBGE para o ano (vale para vítimas e ocorrências); nos demais casos, `taxa_publicada`.
12. Variação e participação por **subconsulta** (ano anterior; indicador-pai ou total do indicador), nunca por função de janela, sempre na mesma unidade; nulas se faltar o termo de comparação ou se a base for zero; no Brasil com recorte, a variação também é nula quando o conjunto de UFs que informaram muda entre os dois anos (ADR 0009). Nunca armazenadas.
13. Toda alteração de modelo vem com migração no mesmo commit. Migração já mesclada na `main` não é editada; corrige-se com outra migração.
14. Constraints vivem no banco (`CheckConstraint(condition=...)` de localidade, `UniqueConstraint(..., nulls_distinct=False)`), não só em validação Python.

**API**
15. API somente leitura: `ReadOnlyModelViewSet` ou `APIView` com `GET`; nada de `create/update/destroy`.
16. Parâmetro de consulta desconhecido → 400. A validação é feita por `apps/api/v1/parametros.py` (`LeitorParametros`), e não pelo django-filter, que ignoraria o parâmetro.
17. `uf` e `regiao` são parâmetros separados (SE = Sergipe ≠ Sudeste).
18. `recorte=total` e `unidade=padrao` são os padrões de `/registros/`; nunca devolver totais misturados com recortes, nem vítimas misturadas com ocorrências, por omissão.
19. Decimais saem como texto; nunca `coerce_to_string=False`.
20. Todo erro sai em Problem Details; 500 sem detalhes técnicos no corpo.
21. Todo valor e toda taxa saem com a fonte (`fonte` do valor; `taxa.fonte` do denominador), em JSON e em CSV. CSV sem linhas de comentário. Catálogos não precisam de fonte por item.
22. Mudança incompatível no contrato exige `/api/v2/`; a v1 não quebra. São incompatíveis: renomear ou remover campo, mudar tipo, casas decimais, valor padrão, regra de validação ou a ordem das colunas do CSV.
23. Nenhuma consulta N+1: listas usam `select_related`/`prefetch_related`, e os testes de API limitam o número de queries (`django_assert_max_num_queries`).
24. Sem `nivel` explícito, `/registros/` e `/populacao/` devolvem um único nível de localidade; misturar Brasil, regiões e UFs só com lista explícita em `nivel` (mesma lógica da regra 18).
25. Arredondamento só na serialização, em `apps/api/v1/campos.py`, com `ROUND_HALF_UP`; `queries.py` nunca arredonda. Ordenação e ranking usam o valor já arredondado.
26. Toda lista tem ordem total e determinística: o critério pedido, depois a ordem padrão do recurso, depois `id`. Ordenação e paginação acontecem no banco, nunca em Python.
27. Erro sai sempre em JSON (Problem Details), mesmo quando o cliente pediu CSV. Toda resposta 200 leva `Vary: Accept`.

**Código e repositório**
28. Configuração só por variável de ambiente; nenhuma credencial, `.env` ou dump de banco no Git. Toda variável nova entra em `.env.example` sem valor real.
29. Dependências só via `uv add`/`uv remove`, com `uv.lock` no mesmo commit. Versões da stack mudam apenas com ADR.
30. Código, nomes de modelos, campos, parâmetros e mensagens em português; identificadores sem acento.
31. Nada de `print` no código da app: use `logging` (comandos usam `self.stdout`).
32. Ruff é a única fonte de estilo; nada de `# noqa` sem justificativa na mesma linha.
33. Não reduzir o limite de cobertura (75%) nem marcar testes como `skip` para passar o CI.

---

## Pendências que exigem decisão da equipe

Não decida sozinho; pergunte antes de implementar o que depender destes pontos. Uma pendência nova entra aqui com o próximo número. Pendência **decidida** já tem decisão da equipe, mas ainda não foi implementada: siga o que está escrito nela e, ao implementar, registre o ADR e marque-a como resolvida.

1. ~~Número de ocorrências~~ — **resolvida (ADR 0004):** importadas; `unidade` no registro, `unidade_padrao` no indicador.
2. ~~Perfis de vítimas~~ — **resolvida (ADR 0004):** fora do escopo.
3. ~~Homicídio de mulheres~~ — **resolvida (ADR 0003):** `homicidio-doloso` → `homicidio-mulheres` → `feminicidio`.
4. ~~Casas decimais na API~~ — **resolvida (ADR 0003):** inteiro em valores absolutos, 2 casas em `taxa.valor` e `variacao`, precisão guardada em `taxa_publicada` (contrato, seção 1.2).
5. ~~Tolerância da validação~~ — **resolvida (ADR 0004):** comparação sem arredondar, tolerância absoluta de 1e-6; a variação publicada é comparada à variação da taxa.
6. ~~Proporções~~ — **resolvida (ADR 0004):** calculadas pela API (`participacao`); T09 e T21 viram conferência.
7. ~~Precisão de `taxa_publicada`~~ — **resolvida (ADR 0003):** 12 casas, arredondadas na importação (ajuste 7).
8. ~~Fonte de `taxa.fonte`~~ — **resolvida (ADR 0005):** `INDICADORES.fonte_taxa` (ajuste 12).
9. ~~Catálogo de fontes~~ — **resolvida (ADR 0005):** `FONTES.slug` e ids fixos 1–5 (ajuste 13).
10. ~~API sem carga concluída~~ — **resolvida (ADR 0005):** 503, `no-store`, sem ETag (contrato, 7.1).
11. ~~Método do teste do RNF02~~ — **resolvida (ADR 0005):** pytest `-m desempenho` no CI, carga real, cliente em processo, p95 por recurso (`tests/desempenho/README.md`).
12. **População de 2012 a 2023** — **decidida, implementação pendente:**
    - **O quê:** carregar em `POPULACAO` as **Projeções da População do IBGE** de 2012 a 2023, para as 27 UFs, as 5 regiões e o Brasil, com `fonte = ibge-projecoes`. 2024 e 2025 continuam com as **Estimativas** (`ibge-estimativas`, os `.ods` atuais), que são as mesmas usadas pelo FBSP na edição de 2026; nunca troque um ano de fonte.
    - **Por quê:** com população em todos os anos, a taxa por 100 mil habitantes passa a ser calculada (regra 11), inclusive nas regiões, e a série de MVI de 2012 a 2023 passa a ser conferida contra a `taxa_publicada` no relatório (RF12). A população também fica pronta para a importação de edições anteriores do Anuário.
    - **Conferência (feita em 30/10/2026):** a população das Projeções coincide exatamente com a população implícita na T02 (valor ÷ taxa publicada × 100 000) nas 33 localidades e em todos os anos de 2012 a 2023; todos os anos entram. A importação deve repetir essa conferência a cada carga (relatório do RF12).
    - **`taxa.fonte`:** em taxa `calculada`, deve indicar a fonte da linha de `POPULACAO` usada no ano (Projeções em 2012–2023, Estimativas em 2024–2025), e não só `INDICADORES.fonte_taxa`. Isso altera o comportamento do ADR 0005 e precisa constar no ADR novo e no `contrato-api.md`.
    - **Ao implementar:** ADR próprio; arquivo do IBGE em `dados/brutos/` com hash no manifesto (regra 1); leitor em `leitores/ibge.py`; contagem de linhas de população atualizada em `docs/importacao.md`; o resumo do modelo neste arquivo ("Taxa por 100 mil habitantes é calculada…") e `docs/modelagem.md` passam a citar 2012–2025.
    - **Arquivo:** `projecoes_2024_tab2_grupo_quinquenal.xlsx` (Projeções das Populações, revisão 2024), já em `dados/brutos/`, listado fora do manifesto em `dados/README.md`. Uma aba (`2) POP_GRUPO QUINQUENAL`), anos de 2000 a 2070 nas colunas (o cabeçalho de ano é fórmula: ler pela posição a partir de 2000 na coluna F). Não há linha de total: a população é a soma dos 19 grupos etários com sexo `Ambos`. Regiões com siglas próprias do IBGE: `NO`, `ND`, `SD`, `SU`, `CO`, que o leitor deve mapear para `N`, `NE`, `SE`, `S`, `CO`.
13. **Edições anteriores do Anuário** — **decidida, implementação pendente:**
    - **O quê:** importar as planilhas das edições anteriores (hoje `anuario-2025.xlsx` e `anuario-2024.xlsx`, já em `dados/brutos/` e listadas fora do manifesto em `dados/README.md`) para estender as séries dos indicadores do escopo.
    - **Edição dona do ano:** cada (indicador, localidade, recorte, unidade, ano) vem da **edição mais recente que o publica**. O mesmo dado em edição anterior entra só como conferência no relatório, como revisão do FBSP, e nunca substitui o da mais recente. É a regra 8 aplicada entre edições.
    - **Ao implementar:** ADR próprio; manifesto com várias planilhas (hoje `processo.py` aceita uma só); um `TABELAS` por edição em `mapeamento.py`, porque a numeração das abas muda (ex.: a T08 de 2026 é a T09 em 2025 e a T10 em 2024); `origem` com o nome do arquivo; contagem esperada por edição; regra 8 e `docs/importacao.md` atualizados.
    - **Já levantado:** a edição de 2025 lê sem erro com o mapeamento atual, trocando só as abas. A de 2024 exige ajustes no leitor: UFs agrupadas por qualidade do dado em T04–T06 e T10 (rótulo na coluna B e linhas "Grupo 1/2/3"), grupo "Ns. Abs." em T16 e T17 e outra hierarquia de cabeçalho na T23. Nas duas edições, o Brasil é a soma das UFs que informaram. A edição de 2024 usa o Censo 2022 como denominador; por isso as taxas de 2022 são calculadas com as Projeções (pendência 12), e as publicadas ficam em `taxa_publicada`.

---

## Commits (Conventional Commits 1.0.0)

Formato:

```
<tipo>(<escopo>): <descrição>

[corpo opcional: o porquê, não o como]

[rodapé opcional: Refs: RF05, RNF10 | BREAKING CHANGE: ...]
```

- **Descrição**: em português, no imperativo, minúscula, sem ponto final, até 72 caracteres ("adiciona", "corrige", "remove").
- **Tipos**: `feat` (funcionalidade), `fix` (correção), `refactor` (sem mudar comportamento), `perf`, `test`, `docs`, `build` (dependências, Dockerfile, `uv.lock`), `ci`, `chore` (manutenção, dados), `style` (só formatação), `revert`.
- **Escopos**: `localidades`, `catalogo`, `registros`, `importacao`, `api`, `dados`, `infra`, `ci`, `docs`, `deps`, `frontend` e `e2e` (fase seguinte).
- **Quebra de contrato**: `!` após o escopo e rodapé `BREAKING CHANGE:`. Na prática, só para `/api/v2/` (regra 22).
- Um commit = uma mudança coerente; modelo + migração + teste juntos. Referencie requisitos no rodapé (`Refs: RF12`).

Exemplos:

```
feat(importacao): adiciona leitura da série histórica de MVI (T02)
fix(api): retorna 400 para parâmetro de consulta desconhecido
feat(registros): calcula variação percentual por subconsulta
test(importacao): verifica idempotência da importação
build(deps): gera uv.lock do backend
chore(dados): atualiza planilha do FBSP e hash no README
docs(adr): registra inclusão da entidade CARGAS
feat(api)!: renomeia campo taxa_publicada

BREAKING CHANGE: campo renomeado em /api/v2/registros/; a v1 permanece inalterada.
```

Branches: `tipo/descricao-curta` (ex.: `feat/ranking-empates`). Integração na `main` só por pull request com o CI aprovado; o squash usa o título no mesmo formato.

---

## Definição de pronto

Uma tarefa só está pronta quando **todos** os itens abaixo são verdadeiros:

- [ ] **Testes passando** — `uv run pytest` sem falhas, com testes novos para o comportamento alterado.
- [ ] **Cobertura ≥ 75%** no backend — garantida pelo `fail_under` do `pyproject.toml`.
- [ ] **Lint limpo** — `ruff check` e `ruff format --check` sem apontamentos.
- [ ] **Migração criada** quando houve mudança de modelo — `makemigrations --check --dry-run` sem pendências, migração no mesmo commit.
- [ ] **Documentação OpenAPI atualizada** — `docs/api/openapi.yaml` regenerado e commitado, `spectacular --validate --fail-on-warn` sem avisos; endpoints e parâmetros novos com descrição e exemplo (`@extend_schema`).

Além disso, quando aplicável: ADR para decisão de arquitetura; `docs/importacao.md`, `docs/contrato-api.md` e `docs/modelagem.md` atualizados junto com o código; `.env.example` atualizado para variável nova.
