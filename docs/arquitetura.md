# Arquitetura

A aplicação segue o estilo REST (Fielding, 2000): o backend expõe os dados tratados como recursos
de uma API somente leitura, e o frontend os consome para montar o dashboard. A API é um produto
reutilizável por terceiros, e não um detalhe do dashboard: tem contrato próprio
([`contrato-api.md`](contrato-api.md)), versionado na URL (`/api/v1/`).

```text
Planilhas FBSP e IBGE ──> importar_anuario ──> PostgreSQL 18
                                                   │
                                     Django + DRF (/api/v1/)
                                                   │
                         Traefik ──> React (Recharts, Leaflet)
```

| Camada | Tecnologia |
| --- | --- |
| Banco de dados | PostgreSQL 18 |
| Backend | Python 3.14, Django 6.1, Django REST Framework, drf-spectacular |
| Importação | pandas, openpyxl e odfpy |
| Frontend | React, Recharts e Leaflet (próxima fase) |
| Testes | pytest (backend), Jest, Playwright e axe-core (próxima fase) |
| Infraestrutura | Proxmox VE, Ubuntu Server, Docker, Traefik e Gunicorn |
| Integração contínua | GitHub Actions |

As versões fixadas estão no `CLAUDE.md` (seção "Stack") e em `backend/pyproject.toml`; mudam só
com ADR.

## Backend

As apps são organizadas por domínio, e não por camada técnica:

| App | Responsabilidade |
| --- | --- |
| `localidades` | Regiões, estados e população (IBGE) |
| `catalogo` | Fontes, indicadores (em hierarquia) e recortes |
| `registros` | A tabela de fatos e os cálculos (`queries.py`): taxa, variação, participação, ordenação, ranking e comparação |
| `importacao` | Leitura das planilhas, agregação regional, validação, gravação idempotente e o comando `importar_anuario` |
| `api` | Camada HTTP da v1: parâmetros, serializers, views, erros, negociação de formato, CSV, paginação e cache |

- **Só a importação grava** (RNF06). O comando `importar_anuario` é a única forma de carga; a
  API apenas lê, e só aceita `GET`, `HEAD` e `OPTIONS`. Os dados de referência fixos (regiões,
  estados, fontes, indicadores) vivem no código, em `referencia.py`, e são revisados em pull
  request. Ver [`importacao.md`](importacao.md) e o ADR 0007.
- **Os cálculos ficam no SQL**, em `apps/registros/queries.py`, por subconsultas correlacionadas
  e nunca por função de janela, para que um filtro por ano não zere a variação. Assim a
  ordenação e a paginação acontecem no banco, e os mesmos cálculos servem `/registros/`,
  `/ranking/` e `/comparacao/` e são testados sem HTTP. O arredondamento acontece só na
  serialização (`apps/api/v1/campos.py`). Ver o ADR 0008 (JIT do PostgreSQL desligado e índice
  das subconsultas).
- **Uma requisição** passa por: método (405) → negociação de formato (406) → carga concluída
  (503) → parâmetros (`LeitorParametros`, 400) → consulta anotada → serialização (JSON ou CSV por
  streaming) → cabeçalhos de cache (`ETag` pela versão da carga e pelo formato, 304). Todo erro
  sai em Problem Details, em JSON.
- **Modelo de dados**: nove entidades, com as restrições no banco (`CHECK` de localidade e de
  situação, chave única `NULLS NOT DISTINCT`). Ver [`modelagem.md`](modelagem.md).

## Qualidade

O CI roda, no backend: Ruff, checagem de migrações pendentes, testes com cobertura mínima de 75%
(no PostgreSQL, por causa do `NULLS NOT DISTINCT`), a importação da planilha real, a comparação do
[`api/openapi.yaml`](api/openapi.yaml) versionado com o esquema gerado e o teste de desempenho do
RNF02 (p95 < 500 ms; ADR 0005). Os testes do frontend e de ponta a ponta rodam quando `frontend/`
ou `e2e/` mudam.
