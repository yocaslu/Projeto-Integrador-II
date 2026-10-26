# Painel do Anuário Brasileiro de Segurança Pública

Plataforma web de análise de dados que estrutura em banco relacional, disponibiliza por meio de
uma API REST própria e visualiza de forma interativa e acessível os principais indicadores do
Anuário Brasileiro de Segurança Pública 2026, do Fórum Brasileiro de Segurança Pública (FBSP),
com taxas calculadas a partir das estimativas populacionais do IBGE.

Projeto Integrador II.

## Estrutura

| Diretório | Conteúdo |
| --- | --- |
| `.github/` | Pipelines do GitHub Actions (CI e implantação) e modelo de pull request. |
| `backend/` | API em Django e Django REST Framework, gerenciada com uv. |
| `frontend/` | Dashboard em React, com Recharts e Leaflet. |
| `e2e/` | Testes de ponta a ponta e de acessibilidade com Playwright e axe-core. |
| `dados/` | Planilhas oficiais do FBSP e do IBGE e relatórios de validação. |
| `infra/` | Compose de produção, Traefik e scripts de implantação. |
| `docs/` | Arquitetura, contrato da API, modelagem, design e decisões (ADR). |

A descrição completa de cada diretório está no roteiro do projeto, na seção "Estrutura do
repositório".

## Primeiros passos

Os arquivos de travamento ainda não foram gerados. Antes do primeiro pull request, gere e
versione os dois:

```bash
cd backend && uv lock          # cria backend/uv.lock
cd ../frontend && npm install  # cria frontend/package-lock.json
cd ../e2e && npm install       # cria e2e/package-lock.json
```

O CI usa `uv sync --locked` e `npm ci`, que falham enquanto esses arquivos não existirem.

## Ambiente de desenvolvimento

Requisitos: Docker com o plugin Compose.

```bash
cp .env.example .env
docker compose up --build
```

| Serviço | Endereço |
| --- | --- |
| Dashboard | http://localhost:5173 |
| API | http://localhost:8000/api/v1/ |
| Documentação da API (Swagger UI) | http://localhost:8000/api/v1/docs/ |

Para carregar os dados no banco:

```bash
docker compose exec backend uv run python manage.py migrate
docker compose exec backend uv run python manage.py importar_anuario
```

## Testes e qualidade

```bash
# backend
cd backend
uv run ruff check . && uv run ruff format --check .
uv run pytest

# frontend
cd frontend && npm test

# ponta a ponta (com o ambiente no ar)
cd e2e && npx playwright test
```

## Convenções

- Commits no padrão [Conventional Commits](https://www.conventionalcommits.org/pt-br/), com o
  escopo do diretório: `feat(api): adiciona endpoint de ranking`, `fix(importacao): ...`.
- Uma branch por tarefa, integrada à `main` por pull request com o CI aprovado.
- Nenhuma credencial no repositório: tudo vem de variáveis de ambiente (veja `.env.example`).

## Fontes dos dados

- Fórum Brasileiro de Segurança Pública (FBSP), Anuário Brasileiro de Segurança Pública 2026.
- Instituto Brasileiro de Geografia e Estatística (IBGE), estimativas populacionais de 2024 e 2025.

## Licença

Distribuído sob a [GNU Affero General Public License v3.0](LICENSE).
