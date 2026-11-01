# Painel do Anuário Brasileiro de Segurança Pública

Consulte, compare e baixe os principais indicadores do Anuário Brasileiro de Segurança Pública, do
Fórum Brasileiro de Segurança Pública (FBSP), por unidade da federação, região e ano, com taxas
calculadas a partir da população do IBGE. São um painel web interativo e uma API REST pública,
somente leitura, sobre um banco PostgreSQL.

Projeto Integrador II. Versão atual: [1.4.0](https://github.com/yocaslu/Projeto-Integrador-II/releases).

![Painel com filtros, cartões da UF, gráfico de evolução, ranking das UFs e mapa do Brasil](docs/imagens/painel-visao-geral.png)

## Comece em cinco minutos

Você só precisa do Docker com o plugin Compose.

```bash
git clone https://github.com/yocaslu/Projeto-Integrador-II.git
cd Projeto-Integrador-II
cp .env.example .env
docker compose up -d --build
docker compose exec backend uv run python manage.py migrate
docker compose exec backend uv run python manage.py importar_anuario
```

A última linha deve terminar com `Nenhuma divergência acima da tolerância.` e informar 3498 registros.
O painel instala as dependências na primeira subida e pode levar um ou dois minutos para responder.

| O que abrir | Endereço |
| --- | --- |
| Painel | <http://localhost:5173> |
| API | <http://localhost:8000/api/v1/metadados/> |
| Documentação interativa da API (Swagger UI) | <http://localhost:8000/api/v1/docs/> |
| Documentação da API (ReDoc) | <http://localhost:8000/api/v1/redoc/> |

Teste a API:

```bash
curl 'http://localhost:8000/api/v1/ranking/?indicador=mvi&ano=2025&formato=csv'
```

## O que você quer fazer?

| Tarefa | Guia |
| --- | --- |
| Usar o painel e interpretar os números | [Guia do painel](docs/guia-do-painel.md) |
| Consultar os dados por `curl`, Python ou planilha | [Guia da API](docs/guia-da-api.md) |
| Instalar, importar, testar, implantar ou publicar uma versão | [Guia de operação](docs/guia-de-operacao.md) |
| Conhecer a arquitetura, as regras e as decisões | [Índice da documentação](docs/README.md) |

## O que há nos dados

| Indicador | Detalhes | Anos |
| --- | --- | --- |
| Mortes Violentas Intencionais (MVI) | Homicídio doloso, latrocínio, lesão corporal seguida de morte e morte decorrente de intervenção policial | 2012 a 2025 |
| Letalidade policial | Total, por corporação e por situação do policial | 2022 a 2025 |
| Feminicídio | Dentro de homicídio de mulheres, com taxa por 100 mil mulheres | 2022 a 2025 |
| Roubo | Total e sete subtipos | 2022 a 2025 |
| Furto | Só veículos e celulares: o Anuário não publica um total de furtos | 2022 a 2025 |

Os dados cobrem as 27 UFs, as cinco regiões e o Brasil e vêm das edições de 2024, 2025 e 2026 do
Anuário. Cada ano sai da edição mais recente que o publica; se uma edição revisou o número, o valor
anterior fica nas notas do dado.

## Testes e qualidade

```bash
docker compose exec backend uv run pytest                 # backend, com cobertura mínima de 75%
docker compose exec frontend npx jest --ci                # painel
```

A lista completa, com a planilha real, o desempenho e os testes de ponta a ponta, está no
[guia de operação](docs/guia-de-operacao.md#testes). Os mesmos testes rodam no GitHub Actions; na
v1.4.0: 651 testes no backend, com 96,78% de cobertura, 38 no painel e 24 de ponta a ponta e
acessibilidade.

## Estrutura

| Diretório | Conteúdo |
| --- | --- |
| `backend/` | API em Django e Django REST Framework; apps `localidades`, `catalogo`, `registros`, `importacao` e `api`. |
| `frontend/` | Painel em React, com Recharts e Leaflet. |
| `e2e/` | Testes de ponta a ponta e de acessibilidade com Playwright e axe-core. |
| `dados/` | Planilhas oficiais do FBSP e do IBGE, com o SHA-256 de cada uma, e relatórios de validação. |
| `infra/` | Compose de produção, Traefik e scripts de implantação, backup e conferência de versões. |
| `docs/` | Guias, arquitetura, contrato da API, importação, modelagem, esquema OpenAPI e decisões (ADR). |
| `.github/` | Workflows de CI, release e implantação, e modelo de pull request. |

## Como contribuir

- Commits no padrão [Conventional Commits](https://www.conventionalcommits.org/pt-br/), em
  português, com o escopo da app: `feat(api): adiciona endpoint de ranking`.
- Uma branch por tarefa, integrada à `main` por pull request com o CI aprovado e a Definição de
  pronto cumprida (checklist no modelo de pull request).
- Nenhuma credencial no repositório: tudo vem de variáveis de ambiente (`.env.example`).
- As regras do projeto estão em [`CLAUDE.md`](CLAUDE.md), e as decisões de arquitetura, em
  [`docs/adr/`](docs/adr/).

## Fontes dos dados

- Fórum Brasileiro de Segurança Pública (FBSP), Anuário Brasileiro de Segurança Pública, edições de
  2024, 2025 e 2026.
- Instituto Brasileiro de Geografia e Estatística (IBGE), projeções da população (2012 a 2023 e taxas
  por 100 mil mulheres), estimativas da população residente (2024 e 2025) e malha das UFs.
- Secretaria Nacional de Trânsito (Senatran), frota de veículos, e Banco Central do Brasil,
  instituições financeiras, como denominadores de taxas publicadas pelo FBSP.

## Licença

Distribuído sob a [GNU Affero General Public License v3.0](LICENSE).
