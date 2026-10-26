# 0001. Repositório único para backend, frontend e infraestrutura

- Data: 2026-10-26
- Situação: aceita

## Contexto

O frontend depende diretamente do contrato da API, e o ambiente de desenvolvimento precisa subir
com um único comando (RNF08). Com repositórios separados, uma mudança no contrato exigiria pull
requests coordenados em dois lugares e pipelines distintos.

## Decisão

Manter backend, frontend, testes de ponta a ponta, dados, infraestrutura e documentação em um
único repositório, em pastas de primeiro nível separadas.

## Consequências

- Uma mudança no contrato e o ajuste no frontend entram no mesmo pull request.
- Um único pipeline no GitHub Actions valida backend, frontend e testes de ponta a ponta.
- Cada pasta mantém suas próprias dependências (`uv.lock` no backend, `package-lock.json` no
  frontend e em `e2e/`), e os jobs do CI rodam cada parte de forma independente.
