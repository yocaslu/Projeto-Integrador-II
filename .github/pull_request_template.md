<!-- Título no formato Conventional Commits, em português: tipo(escopo): descrição (CLAUDE.md, "Commits"). -->

## O que muda

<!-- Descreva a mudança em poucas linhas: o quê e por quê. Cite a seção do contrato, da importação ou o ADR. -->

## Requisitos relacionados

<!-- Ex.: RF05, RNF02 -->

## Como testar

<!-- Comandos e consultas para verificar a mudança. -->

## Definição de pronto

<!-- Todos os itens precisam estar marcados antes do merge (CLAUDE.md, "Definição de pronto"). -->

- [ ] **Testes passando** — `uv run pytest` sem falhas, com testes novos para o comportamento alterado
- [ ] **Cobertura ≥ 75%** no backend — garantida pelo `fail_under` do `pyproject.toml`
- [ ] **Lint limpo** — `uv run ruff check .` e `uv run ruff format --check .` sem apontamentos
- [ ] **Migração criada** quando houve mudança de modelo — `makemigrations --check --dry-run` sem pendências, migração no mesmo commit
- [ ] **Documentação OpenAPI atualizada** — `docs/api/openapi.yaml` regenerado e commitado, `spectacular --validate --fail-on-warn` sem avisos; endpoints e parâmetros novos com descrição (`@extend_schema`)

Quando aplicável:

- [ ] ADR para decisão de arquitetura (`docs/adr/`)
- [ ] `docs/contrato-api.md`, `docs/importacao.md` e `docs/modelagem.md` atualizados junto com o código
- [ ] `.env.example` atualizado para variável nova (sem valor real)
- [ ] Frontend (fase seguinte): `npm test` passando e componentes novos verificados com teclado e leitor de tela
