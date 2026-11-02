# Desenvolvimento

Como testar, contribuir e publicar versões. As regras completas do projeto (decisões, regras
invariáveis e Definição de pronto) estão em [`CLAUDE.md`](../CLAUDE.md); as decisões de
arquitetura, em [adr/](adr/). Para subir o ambiente, veja [operacao.md](operacao.md#2-ambiente-local).

## Testes e qualidade

Com o ambiente no ar e os dados importados:

```bash
# Backend: lint, formatação e testes (cobertura mínima de 75%)
docker compose exec backend uv run ruff check . && docker compose exec backend uv run ruff format --check .
docker compose exec backend uv run pytest
docker compose exec backend uv run pytest -m planilha_real --no-cov    # importa as planilhas completas
docker compose exec backend uv run pytest -m desempenho --no-cov       # RNF02: p95 < 500 ms

# Frontend
docker compose exec frontend npx jest --ci

# Ponta a ponta e acessibilidade (Playwright + axe-core), contra o ambiente com dados
(cd e2e && npm ci && npx playwright install chromium && npx playwright test)
```

| Conjunto | Ferramenta | O que cobre |
| --- | --- | --- |
| Backend | pytest, pytest-django, pytest-cov | Modelos e restrições do banco, cada etapa da importação (com planilhas reduzidas), consultas de taxa, variação, participação e ranking, e cada regra do contrato da API (parâmetros, formatos, CSV, erros, cache). 644 testes, cobertura de 96,7%. |
| Planilha real | pytest `-m planilha_real` | Importação completa: 3.498 registros, 462 populações e nenhuma divergência no relatório. |
| Desempenho | pytest `-m desempenho` | p95 abaixo de 500 ms em `/registros/` (JSON e CSV), `/ranking/` e `/comparacao/` com a carga real ([backend/tests/desempenho/README.md](../backend/tests/desempenho/README.md)). |
| Frontend | Jest, Testing Library | Componentes, filtros, formatação e cliente da API. |
| Ponta a ponta | Playwright, axe-core | Painel carregado nos dois temas sem violações WCAG 2.1 AA, filtros, URL compartilhável, recortes, mapa pelo teclado e clique, fontes no rodapé. |

Sem Docker, os comandos do backend funcionam dentro de `backend/` com `uv run ...` e
`POSTGRES_HOST=localhost`; os testes precisam de um PostgreSQL 18 (o modelo usa
`NULLS NOT DISTINCT`).

## Integração contínua

O GitHub Actions (`.github/workflows/ci.yml`) roda em todo pull request e em todo push na `main`:

- **Backend:** Ruff, migrações pendentes, testes com cobertura, importação da planilha real,
  comparação do [`docs/api/openapi.yaml`](api/openapi.yaml) com o esquema gerado e teste de
  desempenho.
- **Frontend:** Jest e build.
- **Ponta a ponta:** sobe o Compose, importa os dados e roda o Playwright com axe-core.

Os jobs do frontend e de ponta a ponta sempre rodam na `main` e nos releases; em pull requests,
só quando `frontend/` ou `e2e/` mudam.

## Como contribuir

1. Crie uma branch `tipo/descricao-curta` (ex.: `feat/ranking-empates`).
2. Faça commits no padrão [Conventional Commits](https://www.conventionalcommits.org/pt-br/), em
   português, com o escopo da app: `feat(api): adiciona endpoint de ranking`,
   `fix(importacao): ...`.
3. Abra um pull request; o modelo traz o checklist da Definição de pronto (testes, cobertura, lint,
   migração e OpenAPI atualizados).
4. Integre na `main` só com o CI aprovado.

Mudanças que afetam o contrato da API, a importação ou a modelagem atualizam no mesmo pull request
[contrato-api.md](contrato-api.md), [importacao.md](importacao.md) ou [modelagem.md](modelagem.md).
Nenhuma credencial vai para o repositório: tudo vem de variáveis de ambiente (`.env.example`).

## Comandos úteis

| Tarefa | Comando |
| --- | --- |
| Criar migrações | `docker compose exec backend uv run python manage.py makemigrations` |
| Regerar o esquema OpenAPI | `docker compose exec -T backend uv run python manage.py spectacular --validate --fail-on-warn > docs/api/openapi.yaml` |
| Corrigir lint e formatação | `docker compose exec backend uv run ruff check --fix . && docker compose exec backend uv run ruff format .` |
| Inspecionar uma planilha | `docker compose exec backend uv run python manage.py inspecionar_planilha T03 T08` |
| Adicionar dependência Python | `cd backend && uv add <pacote>==<versão>` |
| Gerar a malha do mapa | `cd frontend && npm run malha` |

## Versões e releases

As versões seguem o [SemVer](https://semver.org/lang/pt-BR/) e são publicadas como
[releases](https://github.com/yocaslu/Projeto-Integrador-II/releases), com imagens Docker no GitHub
Container Registry. A versão da aplicação é independente da versão da API (`/api/v1/`), que só muda
com quebra de contrato ([ADR 0010](adr/0010-versionamento-e-releases.md)).

| Versão | Data | Principais mudanças |
| --- | --- | --- |
| 1.0.0 | 30/10/2026 | Primeira versão estável: importação da edição de 2026, API v1 completa e painel com filtros, cartões, evolução, ranking, mapa e CSV. |
| 1.1.0 | 30/10/2026 | População de 2012 a 2023 pelas projeções do IBGE: taxas calculadas em toda a série de MVI ([ADR 0011](adr/0011-populacao-2012-2023.md)). |
| 1.2.0 | 30/10/2026 | Edições de 2024 e 2025 do Anuário: dados de 2022 e 2023 para todos os indicadores, com as revisões do FBSP registradas ([ADR 0012](adr/0012-edicoes-anteriores-do-anuario.md)). |
| 1.3.0 | 30/10/2026 | Painel com unidade, recortes de corporação e situação, critério do ranking e filtros na URL; carregamento sob demanda dos gráficos e do mapa. |
| 1.4.0 | 30/10/2026 | Tema escuro. |

Para publicar uma versão:

1. Em um pull request, suba a versão nos arquivos do backend e do frontend:

   ```bash
   (cd frontend && npm version X.Y.Z --no-git-tag-version)
   sed -i 's/^version = ".*"/version = "X.Y.Z"/' backend/pyproject.toml
   (cd backend && uv lock)
   ```

2. Depois do merge, crie a tag na `main`:

   ```bash
   git switch main && git pull
   git tag -a vX.Y.Z -m "vX.Y.Z"
   git push origin vX.Y.Z
   ```

O workflow `release.yml` confere a tag, roda o CI completo, publica as imagens (`X.Y.Z`, `X.Y` e
`latest`) e cria o release. Ele não implanta; veja [operacao.md](operacao.md#5-produção).
