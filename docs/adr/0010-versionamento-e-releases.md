# 0010. Versionamento da aplicação e releases

- Data: 2026-10-30
- Situação: aceita

## Contexto

O projeto chegou a uma versão estável, mas não tinha tags nem releases. As imagens só podiam sair
do workflow de deploy, identificadas pelo SHA do commit e por `latest`, então não havia como
apontar para "a versão apresentada" nem voltar a ela com facilidade. A aplicação é implantada, não
instalada como dependência por terceiros: pacotes npm ou PyPI não trariam benefício.

## Decisão

1. **Os pacotes são imagens Docker no GitHub Container Registry**:
   `ghcr.io/yocaslu/projeto-integrador-ii/backend` e `.../frontend`.
2. **A versão segue o SemVer** (`vX.Y.Z`), e os Conventional Commits indicam o incremento: `feat`
   sobe a minor, `fix` sobe a patch. Prévias (`-rc`) ficam fora por enquanto.
3. **A tag é a única origem de um release.** O workflow `release.yml` só aceita tag que aponte para
   um commit da `main` e que seja igual às versões de `frontend/package.json`,
   `frontend/package-lock.json`, `backend/pyproject.toml` e `backend/uv.lock`. Depois roda o CI
   completo, publica as imagens com as tags `X.Y.Z`, `X.Y` e `latest` e cria o GitHub Release.
4. **`latest` é sempre o último release.** O workflow de deploy publica só com o SHA, para um deploy
   de commit qualquer não sobrescrever a versão estável.
5. **Release e deploy são separados.** Publicar uma versão não implanta nada.
6. **A versão da aplicação não acompanha a da API.** `v2.0.0` da aplicação não implica `/api/v2/`; a
   API só muda de versão com quebra de contrato (regra 22).
7. **Os dados não entram nas imagens.** As notas de cada release citam a versão da carga, calculada
   a partir dos hashes do manifesto em `dados/README.md`.

## Consequências

- Voltar a uma versão é escolher a tag da imagem (`TAG=1.0.0` no `compose.prod.yml`). Migrações já
  aplicadas não são revertidas por isso: voltar por cima de uma migração exige avaliação própria.
- Publicar exige um commit que suba as quatro versões, por pull request, antes da tag.
- Se um release falhar depois de publicar as imagens, a correção é uma nova versão; tags publicadas
  não são reaproveitadas.
- Publicar uma correção de versão antiga (`v1.0.1` depois de `v1.1.0`) moveria `latest` para trás. Se
  isso for necessário, a automação precisa ser revista.
- A automação do incremento e do changelog fica de fora: as notas vêm dos pull requests.
