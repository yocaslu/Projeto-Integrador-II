# CLAUDE.md

Plataforma de análise do **20º Anuário Brasileiro de Segurança Pública (FBSP, 2026)**: banco relacional (PostgreSQL 18) → API REST somente leitura (Django + DRF) → dashboard (React). Licença AGPL-3.0.

**Fonte da verdade:** o documento "Roteiro" do projeto (seções Requisitos, Contrato da API e Modelagem de dados), até que seja transcrito para `docs/contrato-api.md` e `docs/modelagem.md`. A importação está especificada em `docs/importacao.md`. Se o código divergir desses documentos, pare e pergunte antes de "corrigir" qualquer um dos lados.

---

## Escopo atual

**O foco agora é exclusivamente o backend: modelos, importação da planilha e API `/api/v1/`.**

- O frontend (React, Recharts, Leaflet) e os testes de ponta a ponta (Playwright + axe-core) **vêm depois**. Não crie, altere nem instale nada em `frontend/` ou `e2e/` sem pedido explícito, e suba só `db` e `backend` no Docker Compose.
- Ordem de entrega: `localidades` e `catalogo` → `importacao` (comando + relatório de validação) → `registros` (consultas de taxa, variação, ranking, comparação) → `api` (endpoints, filtros, erros, CSV, cache) → documentação OpenAPI.
- Requisitos em foco: RF01, RF02, RF05, RF07–RF13, RNF02, RNF05–RNF12. Os de interface (RF03, RF04, RF06, RNF01, RNF03) ficam para a fase do frontend, mas o contrato da API já precisa atendê-los.

---

## Comandos

Rodam a partir da raiz do repositório. Serviços do Compose: `db`, `backend` e `frontend` (este fica desligado nesta fase).

**Primeira vez**
```bash
cp .env.example .env
(cd backend && uv lock)        # só se backend/uv.lock não existir: o Dockerfile e o CI usam --locked
docker compose up -d --build db backend
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
| Testes com cobertura (≥ 75%) | `docker compose exec backend uv run pytest` |
| Um teste específico | `docker compose exec backend uv run pytest tests/importacao/test_normalizacao.py -k inexistente` |
| Lint e formatação (verificar) | `docker compose exec backend uv run ruff check . && docker compose exec backend uv run ruff format --check .` |
| Lint e formatação (corrigir) | `docker compose exec backend uv run ruff check --fix . && docker compose exec backend uv run ruff format .` |
| Gerar o esquema OpenAPI versionado | `docker compose exec -T backend uv run python manage.py spectacular --validate --fail-on-warn > docs/api/openapi.yaml` |
| Adicionar dependência | `cd backend && uv add <pacote>==<versão>` (ou `uv add --dev`) |

Notas:
- `uv run pytest` já aplica `--cov` e `fail_under = 75` pelo `pyproject.toml`; não repita as opções.
- `importar_anuario` lê `--dados` (padrão `DADOS_BRUTOS_DIR=/dados/brutos`) e grava o relatório em `--relatorio` (padrão `DADOS_RELATORIOS_DIR=/dados/relatorios`). `./dados` é montado em `/dados` no container. As opções `--somente-validar` e `--estrito` estão especificadas em `docs/importacao.md` e ainda serão implementadas.
- Sem Docker, os mesmos comandos funcionam dentro de `backend/` com `uv run ...`, apontando `POSTGRES_HOST=localhost`.

Sequência completa em ambiente limpo: subir → `migrate` → `importar_anuario` → `pytest`.

URLs locais: API em `http://localhost:8000/api/v1/`, Swagger em `/api/v1/docs/`, ReDoc em `/api/v1/redoc/`, esquema em `/api/v1/schema/`.

---

## Decisões do projeto

### Stack (versões fixadas — não atualize sem ADR)
Python 3.14.9 · Django 6.1.2 · DRF 3.18.3 · django-filter 26.2 · drf-spectacular 0.30.0 · psycopg 3.3.6 · pandas 3.0.6 · openpyxl 3.1.5 · odfpy 1.4.1 · PostgreSQL 18 · uv 0.13.5 (`uv.lock` versionado) · Ruff 0.17.2 · pytest 9.1.1 + pytest-django 4.14.0 + pytest-cov 7.1.0 · Gunicorn 26.2.2 · Docker + Traefik em VMs Ubuntu Server 26.04 (Proxmox VE) · GitHub Actions. Frontend (fase seguinte): React, Recharts, Leaflet, Jest, Playwright + axe-core.

### Arquitetura
- REST (Fielding, 2000): cliente e servidor desacoplados; a API é um produto reutilizável por terceiros, não um detalhe do dashboard.
- Apps do backend organizadas por **domínio**: `localidades`, `catalogo`, `registros`, `importacao`, `api`.
- `importacao` é a **única** app que grava no banco; `api` apenas lê (RNF06).
- Cálculos (taxa, variação, ranking com empates, comparação) ficam em `apps/registros/queries.py`, fora das views, para serem reutilizados por `/registros/`, `/ranking/` e `/comparacao/` e testados sem HTTP.
- Testes rodam no PostgreSQL (não SQLite), porque o modelo usa `NULLS NOT DISTINCT`.

### Indicadores do escopo
MVI (indicador-síntese), letalidade policial (mortes decorrentes de intervenção policial), feminicídio, roubo (total e subtipos) e furto (só subtipos: veículo e celular; o Anuário não publica total de furtos).

### Modelo de dados (resumo)
- `REGIOES` (5 regiões + Brasil, `tipo` = `regiao`|`pais`); `ESTADOS` (27 UFs, cada uma em uma região).
- `REGISTROS_ANUAIS` é a tabela de fatos: um valor por (localidade, indicador, recorte, ano), com fonte.
- Localidade = `estado_id` **ou** `regiao_id`, exatamente um (`CheckConstraint`).
- Unicidade em (estado, regiao, indicador, recorte, ano) com `UniqueConstraint(..., nulls_distinct=False)`.
- `INDICADORES` em hierarquia (`indicador_pai`): MVI → homicídio doloso (→ feminicídio), latrocínio, lesão corporal seguida de morte, morte decorrente de intervenção policial; Roubo → veículo, celular, transeunte, residência, estabelecimento comercial, instituição financeira, carga; Furto (agrupador sem registros) → veículo, celular.
- Indicadores-pai e o total do Brasil são **importados**, nunca somados. As regiões são importadas quando o FBSP as publica (só MVI, T02); nos demais casos são **calculadas na importação** como soma das UFs (`metodo = soma_ufs`). Se alguma UF da região estiver "...", a região fica nula (`nao_disponivel`). Detalhes em `docs/importacao.md`, seção 4.9.
- Características de vítimas ou agentes são **recortes** (`RECORTES` + `RECORTE_ITENS`, pares dimensão/valor, ex.: corporação = Polícia Militar + situação = em serviço). Registro sem recorte = total.
- `situacao`: `informado` | `inexistente` (“-” → valor 0) | `nao_disponivel` (“...” → valor nulo). Notas do FBSP vão em `observacao`.
- `unidade` (vítimas, ocorrências, percentual) e `base_taxa` (100 mil habitantes; 100 mil mulheres; 100 mil veículos; 100 instituições) ficam em `INDICADORES`.
- Taxa por 100 mil habitantes é **calculada** a partir de `POPULACAO` (IBGE 2024 e 2025, as mesmas estimativas usadas pelo FBSP); nos demais casos (outras bases e série MVI 2012–2023) usa-se `taxa_publicada`. A variação percentual é calculada na consulta e nunca armazenada.

Ajustes ao modelo do roteiro, já decididos (registrar em ADR ao implementar):
1. `INDICADORES.slug` (único) — exigido pelo contrato da API.
2. `ESTADOS.codigo_ibge` e `REGIOES.codigo_ibge` — chave estável para a malha do mapa e para cruzamentos futuros.
3. `RECORTES.chave` (única, pares ordenados `dimensao=valor;...`) — torna a criação de recortes idempotente.
4. `REGISTROS_ANUAIS.origem` (ex.: `T08!D15`) — rastreabilidade de cada valor até a célula da planilha.
5. Nova entidade `CARGAS` (versao, sha256 de cada arquivo, iniciada_em, concluida_em, status, total_registros) — alimenta `/metadados/` e o ETag.
6. `POPULACAO` recebe a mesma CHECK de localidade e unicidade (localidade, ano) `NULLS NOT DISTINCT`.
7. `taxa_publicada` guarda a taxa **sem arredondar**, como publicada (a planilha traz até 15 casas): `DecimalField(max_digits=24, decimal_places=12)`. `valor`: `DecimalField(max_digits=18, decimal_places=4)`.
8. `REGISTROS_ANUAIS.metodo` (`publicado` | `soma_ufs`, padrão `publicado`) — distingue o valor lido da planilha do agregado regional calculado pelo projeto; exposto na API (RF11). `origem` com `max_length=200`, porque a linha regional lista as células somadas.

### Contrato da API (resumo)
- Prefixo `/api/v1/`, `URLPathVersioning`. Mudança incompatível → `/api/v2/`; a v1 continua no ar.
- Só `GET`, `HEAD`, `OPTIONS`; o resto → 405.
- Nomes em português, `snake_case`, iguais aos atributos do modelo. UF e região por sigla; indicador por slug.
- Recursos: `regioes`, `estados`, `indicadores`, `recortes`, `fontes`, `populacao`, `registros`, `ranking`, `comparacao`, `metadados`, `schema`/`docs`/`redoc`.
- `/registros/` aceita `nivel`, `uf`, `regiao`, `indicador`, `incluir_subtipos`, `ano`/`ano_min`/`ano_max`, `recorte` (`total` padrão | `todos` | id), `situacao`, `ordenar`; listas separadas por vírgula.
- Cada registro traz `localidade`, `indicador`, `recorte`, `valor`, `situacao`, `taxa` (`valor`, `base`, `origem` = `calculada`|`publicada`), `taxa_publicada`, `variacao` (`ano_referencia`, `valor_pct`, `taxa_pct`), `fonte`, `observacao`.
- Decimais serializados como **texto** (`COERCE_DECIMAL_TO_STRING = True`).
- JSON por padrão; CSV com `formato=csv` ou `Accept: text/csv` (streaming, máx. 50 mil linhas, colunas `fonte` e `situacao`, sem linhas de comentário).
- Paginação por página só em `/registros/` e `/populacao/` (`pagina`, `tamanho` padrão 100, máx. 1000); demais recursos com `pagination_class = None`.
- `/ranking/`: critério padrão `taxa`; empates com mesma posição (1, 2, 2, 4); sem dado → fim da lista, posição nula.
- Erros em Problem Details (RFC 9457), `application/problem+json`, com lista `erros` em validações (já implementado em `apps/api/erros.py`).
- Cache: `Cache-Control: public, max-age=86400` + ETag derivado da versão da carga.

### Requisitos (referência rápida)

| Código | Resumo |
| :--- | :--- |
| RF01 | Importar e normalizar planilha do FBSP e estimativas do IBGE |
| RF02 | API por estado, região, ano, indicador, subtipo e recorte |
| RF05 | Taxas por 100 mil hab. (IBGE) e variação percentual |
| RF07 | Exportação CSV |
| RF08 | Documentação OpenAPI interativa |
| RF09 | Endpoint de metadados |
| RF10 | Ranking das UFs |
| RF11 | Situação do dado e notas metodológicas junto a cada valor |
| RF12 | Importação idempotente + relatório de validação das taxas |
| RF13 | Comparação UF × região × Brasil |
| RNF02 | p95 < 500 ms em consultas filtradas por UF, ano e indicador (teste automatizado) |
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

Árvore atual com as mudanças propostas: ✚ a criar, ✎ a ajustar. Itens sem marca já existem.

```
projeto-integrador-ii/
├── CLAUDE.md
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                     ✎ incluir makemigrations --check e diff do docs/api/openapi.yaml
│   │   └── deploy.yml
│   └── pull_request_template.md       ✎ checklist da Definição de pronto
├── backend/
│   ├── pyproject.toml · Dockerfile · manage.py · .python-version
│   ├── uv.lock                        ✚ gerar com `uv lock` (o build e o CI dependem dele)
│   ├── config/settings/               # base.py, dev.py, test.py, prod.py
│   ├── apps/
│   │   ├── localidades/               # Regiao, Estado, Populacao
│   │   │   └── referencia.py          ✚ 5 regiões + Brasil + 27 UFs (sigla, nome, código IBGE, aliases)
│   │   ├── catalogo/                  # Fonte, Indicador, Recorte, RecorteItem
│   │   │   └── referencia.py          ✚ hierarquia de indicadores (slug, pai, unidade, base_taxa)
│   │   ├── registros/                 # RegistroAnual
│   │   │   └── queries.py             # taxa, variação (subconsulta), ranking com empates, comparação
│   │   ├── importacao/
│   │   │   ├── models.py              ✚ Carga
│   │   │   ├── mapeamento.py          ✚ especificação declarativa das tabelas T02–T21
│   │   │   ├── leitores/              # fbsp.py (openpyxl), ibge.py (pandas + odfpy)
│   │   │   ├── normalizacao.py        # “-”, “...”, Decimal  ✎ notas de rodapé e localidades
│   │   │   ├── linhas.py              # Chave, Linha, Localidade (nível + sigla), Metodo
│   │   │   ├── agregacao.py           # regiões = soma das UFs; confere Brasil e T02
│   │   │   ├── gravacao.py            ✚ upsert idempotente
│   │   │   ├── validacao.py           # relatório de divergências  ✎ tolerância (ver Pendências)
│   │   │   └── management/commands/
│   │   │       ├── importar_anuario.py
│   │   │       └── inspecionar_planilha.py ✚ lista abas, âncoras e caminhos de cabeçalho
│   │   └── api/
│   │       ├── v1/                    # urls, views, serializers, filtros
│   │       └── erros.py · renderizadores.py · paginacao.py · cache.py
│   └── tests/                         # espelha apps/: importacao/, registros/, api/, desempenho/
│       ├── localidades/ · catalogo/   ✚
│       ├── conftest.py
│       └── fixtures/                  # planilhas reduzidas (recortes da real, poucas UFs)
├── frontend/                          ⏸ fase seguinte
├── e2e/                               ⏸ fase seguinte
├── dados/
│   ├── README.md                      # origem e SHA-256 de cada arquivo
│   ├── brutos/                        # anuario-2026.xlsx, POP2024_20241230.ods, POP2025_20260828.ods
│   └── relatorios/                    # gerados pela importação (fora do Git)
├── infra/                             # compose.prod.yml, traefik/
├── docs/
│   ├── importacao.md                  # mapeamento da planilha e algoritmo de extração
│   ├── contrato-api.md · modelagem.md ✚ transcrição das seções do roteiro
│   ├── api/openapi.yaml               ✚ esquema gerado e versionado (diff verificado no CI)
│   └── adr/                           ✚ 0001-api-rest.md, 0002-ajustes-modelo.md, ...
├── docker-compose.yml · .env.example · .editorconfig · .gitignore · LICENSE · README.md
```

Motivos das mudanças:
- **`referencia.py` em `localidades` e `catalogo`**: dados de referência fixos vivem no código, revisados em PR, e são carregados pelo `importar_anuario` antes dos fatos.
- **`importacao` em leitura → normalização → gravação → validação**: cada etapa testável isoladamente; o mapeamento é dado, não lógica espalhada.
- **`inspecionar_planilha`**: a planilha muda de layout entre edições; o comando mostra os caminhos de cabeçalho antes de alguém ajustar `mapeamento.py`.
- **`docs/api/openapi.yaml` versionado**: toda mudança de contrato fica visível no diff do PR e permite exigir "OpenAPI atualizado" na Definição de pronto.

---

## Importação da planilha

Especificação completa (tabelas, colunas, regras e pseudocódigo) em **`docs/importacao.md`**. Leia antes de mexer em `apps/importacao/`.

Resumo:
- **Lidas:** T02 (MVI 2012–2025), T03 (homicídio doloso), T04 (latrocínio), T05 (lesão corporal seguida de morte), T08 (MDIP por corporação e situação), T11 (roubo/furto de veículo), T12 (roubo/furto de celular), T14 (roubo a estabelecimento comercial, residência, transeunte), T15 (roubo a instituição financeira, de carga e total), T21 (homicídio de mulheres e feminicídio).
- **Só conferência:** T01 (MVI 2024–2025; idêntica a T02).
- **Ignoradas:** painéis (P), gráficos (G), quadros (Q) e as demais tabelas.
- **População:** aba `BRASIL_E_UFs` dos dois `.ods` do IBGE, já com totais de regiões e Brasil.
- **Volume esperado:** 1.782 registros (1.582 lidos + 200 regionais calculados, dos quais 24 nulos) e 66 linhas de população. Contagem diferente é falha da importação.

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
4. Indicadores-pai e o total do Brasil são **importados**, nunca somados a partir dos subtipos ou das UFs. Regiões: importadas quando publicadas (T02); nos demais casos, calculadas só em `agregacao.py`, como soma das UFs da região, apenas para unidade absoluta (vítimas, ocorrências), no mesmo indicador, recorte e ano, com `metodo = soma_ufs`. Se alguma UF da região estiver "...", a região fica `NULL`/`nao_disponivel`, nunca soma parcial. Taxas nunca são somadas nem tiradas em média. Agregado publicado que divirja da soma das UFs que informaram aborta a importação.
5. Não existe total de furtos. O indicador `furto` não tem registros próprios; nunca calcule nem exiba um total. Os blocos "Roubo e Furto" das tabelas T11 e T12 não são importados.
6. “-” → `valor = 0`, `situacao = inexistente`. “...” → `valor = NULL`, `situacao = nao_disponivel`. Célula vazia → `nao_disponivel` com aviso no relatório. Qualquer outro texto aborta a importação com a célula de origem na mensagem.
7. Localidade não reconhecida, coluna de cabeçalho não resolvida ou contagem diferente da esperada abortam a importação. Nunca pular linha em silêncio.
8. Cada (indicador, localidade, recorte, ano) tem **uma** tabela dona em `mapeamento.py`; outra tabela com o mesmo dado só entra como conferência no relatório.
9. Recortes de perfil de vítimas existem só para o Brasil; não inventar recorte por UF.

**Banco e cálculos**
10. Valores, taxas e populações usam `DecimalField` (NUMERIC). `float` é proibido em modelos, cálculos e serializers; converter célula com `Decimal(str(v))`.
11. Taxa calculada só quando a base é 100 mil habitantes e há população do IBGE para o ano; nos demais casos, `taxa_publicada`. Unidade percentual → taxa nula.
12. Variação percentual por **subconsulta** ao ano anterior, nunca por função de janela; nula se faltar um dos anos ou se a base for zero. Nunca armazenada.
13. Toda alteração de modelo vem com migração no mesmo commit. Migração já mesclada na `main` não é editada; corrige-se com outra migração.
14. Constraints vivem no banco (`CheckConstraint(condition=...)` de localidade, `UniqueConstraint(..., nulls_distinct=False)`), não só em validação Python.

**API**
15. API somente leitura: `ReadOnlyModelViewSet` ou `APIView` com `GET`; nada de `create/update/destroy`.
16. Parâmetro de consulta desconhecido → 400 (o padrão do django-filter, de ignorar, é desligado).
17. `uf` e `regiao` são parâmetros separados (SE = Sergipe ≠ Sudeste).
18. `recorte=total` é o padrão de `/registros/`; nunca devolver totais misturados com recortes por omissão.
19. Decimais saem como texto; nunca `coerce_to_string=False`.
20. Todo erro sai em Problem Details; 500 sem detalhes técnicos no corpo.
21. Toda resposta e todo CSV indicam a fonte (FBSP/IBGE). CSV sem linhas de comentário.
22. Mudança incompatível no contrato exige `/api/v2/`; a v1 não quebra.
23. Nenhuma consulta N+1: listas usam `select_related`/`prefetch_related`, e os testes de API limitam o número de queries (`django_assert_max_num_queries`).

**Código e repositório**
24. Configuração só por variável de ambiente; nenhuma credencial, `.env` ou dump de banco no Git. Toda variável nova entra em `.env.example` sem valor real.
25. Dependências só via `uv add`/`uv remove`, com `uv.lock` no mesmo commit. Versões da stack mudam apenas com ADR.
26. Código, nomes de modelos, campos, parâmetros e mensagens em português; identificadores sem acento.
27. Nada de `print` no código da app: use `logging` (comandos usam `self.stdout`).
28. Ruff é a única fonte de estilo; nada de `# noqa` sem justificativa na mesma linha.
29. Não reduzir o limite de cobertura (75%) nem marcar testes como `skip` para passar o CI.

---

## Pendências que exigem decisão da equipe

Não decida sozinho; pergunte antes de implementar o que depender destes pontos.

1. **Número de ocorrências** (T03–T05 trazem vítimas e ocorrências): por ora só **vítimas** é importado, coerente com a definição de MVI. Importar ocorrências exigiria indicadores próprios.
2. **Perfis de vítimas** (sexo, raça/cor, faixa etária): estão nos painéis P01, P03 e P06, em blocos de dados de gráfico, sem cabeçalho tabular. Ficam fora da primeira carga; se entrarem, o mapeamento será por intervalo de células fixo.
3. **Homicídio de mulheres** (T21): proposto como `homicidio-mulheres` (filho de `homicidio-doloso`, base 100 mil mulheres). Falta decidir se o feminicídio passa a ser filho dele, e não de `homicidio-doloso`.
4. **Casas decimais na API:** as taxas são guardadas com precisão total; falta decidir quantas casas a API expõe (sugestão: 2 em `taxa.valor` e `variacao`, precisão total em `taxa_publicada`).
5. **Tolerância da validação:** `validacao.py` arredonda a 0,1 e tolera 0,1, mas as taxas do FBSP batem com o cálculo pela população do IBGE até ~1e-14. Sugestão: comparar com tolerância de 1e-6.
6. **Proporções** (T09 e coluna "Proporção" da T21): derivadas de outros indicadores; não importadas por ora.

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

Além disso, quando aplicável: ADR para decisão de arquitetura; `docs/importacao.md` (e, quando existirem, `docs/contrato-api.md` e `docs/modelagem.md`) atualizados junto com o código; `.env.example` atualizado para variável nova.
