# Guia de operação

Como instalar, carregar os dados, testar, implantar e publicar uma versão. Os comandos rodam a partir
da raiz do repositório.

## Ambiente local

Requisito: Docker com o plugin Compose.

```bash
cp .env.example .env
docker compose up -d --build
docker compose exec backend uv run python manage.py migrate
docker compose exec backend uv run python manage.py importar_anuario
```

| Serviço | Endereço | Acesso |
| --- | --- | --- |
| Painel (`frontend`) | <http://localhost:5173> | Rede local; repassa as chamadas à API |
| API (`backend`) | <http://localhost:8000/api/v1/> | Só o próprio computador |
| PostgreSQL (`db`) | `localhost:5432` | Só o próprio computador |

| Tarefa | Comando |
| --- | --- |
| Subir sem reconstruir | `docker compose up -d` |
| Parar | `docker compose down` |
| Parar e apagar o banco | `docker compose down -v` |
| Ver os logs | `docker compose logs -f backend` |
| Abrir um shell | `docker compose exec backend bash` |

Sem Docker, os comandos do backend funcionam dentro de `backend/` com `uv run ...`, desde que haja um
PostgreSQL 18 e `POSTGRES_HOST=localhost`.

## Importar os dados

```bash
docker compose exec backend uv run python manage.py importar_anuario
```

O comando confere o SHA-256 dos arquivos de `dados/brutos/` contra `dados/README.md`, grava tudo em
uma transação e gera o relatório em `dados/relatorios/`. A saída esperada é:

```text
Carga 764af7ef35c3 concluída: 3498 registros (460 regionais calculados) e 462 populações.
  divergencia: 0
  aviso: 0
  informacao: 1557
Nenhuma divergência acima da tolerância.
```

Pode rodar de novo: não duplica nada nem muda os `id`s. Se algo falhar, nada é gravado, e a carga
anterior continua valendo.

| Opção | Efeito |
| --- | --- |
| `--somente-validar` | Lê, confere e gera o relatório sem gravar no banco. |
| `--estrito` | Termina com erro se o relatório tiver divergência. |
| `--dados`, `--relatorio`, `--manifesto` | Outros diretórios de entrada e saída e outro arquivo de hashes. |

### Ler o relatório

`validacao-<versao>.md` resume as comparações; `validacao-<versao>.csv` traz um apontamento por linha.

- **Divergência:** a taxa, a variação ou a participação difere do valor publicado em mais de 1e-6.
  Investigue antes de publicar.
- **Aviso:** por exemplo, célula vazia ou registro órfão.
- **Informação:** não exige ação; registra revisões entre edições, somas parciais e diferenças já
  explicadas, como as taxas da edição de 2024, que usam o Censo.

### Incorporar uma nova edição

1. Adicione a planilha a `dados/brutos/`, sem editar as existentes, e registre o hash em
   `dados/README.md`, em um commit próprio.
2. Inspecione a estrutura: `docker compose exec backend uv run python manage.py inspecionar_planilha T03 T08`.
3. Ajuste `apps/importacao/mapeamento.py` e a contagem esperada, seguindo [`importacao.md`](importacao.md).
4. Valide com `importar_anuario --somente-validar --estrito`.

Quando a contagem é diferente da esperada, a localidade não é reconhecida ou uma célula tem texto
inesperado, a importação é interrompida de propósito, com a célula na mensagem.

## Testes

Com o ambiente no ar:

```bash
docker compose exec backend uv run ruff check .                      # lint
docker compose exec backend uv run ruff format --check .             # formatação
docker compose exec backend uv run python manage.py makemigrations --check --dry-run
docker compose exec backend uv run pytest                            # cobertura mínima de 75%
docker compose exec backend uv run pytest tests/importacao/test_normalizacao.py -k inexistente
docker compose exec backend uv run pytest -m planilha_real --no-cov  # importa a planilha completa
docker compose exec backend uv run pytest -m desempenho --no-cov     # p95 < 500 ms
docker compose exec frontend npx jest --ci                           # painel
(cd e2e && npm ci && npx playwright install chromium && npx playwright test)  # ponta a ponta
```

Os testes de ponta a ponta precisam dos dados importados e rodam em desktop e celular, com verificação
do axe-core. Para testar outro endereço, defina `BASE_URL`.

Se mudar a API, regenere o esquema versionado, que o CI compara:

```bash
docker compose exec -T backend uv run python manage.py spectacular --validate --fail-on-warn > docs/api/openapi.yaml
```

### O que o CI executa

O workflow `ci.yml` roda em todo pull request e em todo push na `main`:

| Job | Etapas |
| --- | --- |
| Backend | Ruff, migrações pendentes, pytest com cobertura, importação da planilha real, comparação do `openapi.yaml` e desempenho |
| Frontend | Jest e build de produção |
| Ponta a ponta | Sobe o Compose, importa os dados e roda Playwright e axe-core |

Em pull request, os dois últimos só rodam se `frontend/` ou `e2e/` mudarem; na `main` e em release,
sempre rodam.

## Produção

> A implantação abaixo vem dos arquivos de `infra/`, mas ainda não foi executada: o workflow `deploy.yml`
> nunca rodou. Trate a primeira execução como um teste.

Arquitetura: Traefik (HTTPS e roteamento), Gunicorn (API), nginx (painel estático) e PostgreSQL 18, em
contêineres definidos em `infra/compose.prod.yml`.

### Primeira instalação

Em uma VM com Docker, DNS apontando para ela e as portas 80 e 443 abertas:

```bash
sudo git clone https://github.com/yocaslu/Projeto-Integrador-II.git /opt/anuario
cd /opt/anuario
cp .env.example .env
```

Edite o `.env`:

| Variável | Valor |
| --- | --- |
| `DJANGO_SECRET_KEY` | Valor longo e aleatório |
| `DJANGO_ALLOWED_HOSTS` | O domínio, como `anuario.exemplo.org` |
| `POSTGRES_PASSWORD` | Senha forte |
| `DOMINIO` e `ACME_EMAIL` | Domínio e e-mail do certificado Let's Encrypt |

As demais podem ficar como em `.env.example`. Suba uma versão publicada e carregue os dados, que não
ficam nas imagens:

```bash
export TAG=1.4.0
COMPOSE="docker compose -f infra/compose.prod.yml --env-file .env"
$COMPOSE pull
$COMPOSE up -d
$COMPOSE exec backend uv run --no-dev python manage.py migrate --noinput
$COMPOSE exec backend uv run --no-dev python manage.py importar_anuario
```

Confira: `curl -I https://<domínio>/api/v1/metadados/` deve responder 200, com `ETag`.

### Atualizar ou voltar uma versão

Repita `pull`, `up -d` e `migrate` com outro `TAG`. As imagens têm as tags `X.Y.Z`, `X.Y` e `latest`.
Voltar a imagem não reverte migrações já aplicadas: avalie antes de voltar por cima de uma migração
(ADR 0010). Depois de uma versão com novos dados, rode `importar_anuario`; a nova carga muda o `ETag` e
invalida o cache.

O workflow manual `deploy.yml` faz o mesmo por SSH, a partir de um commit, e exige os segredos
`DEPLOY_HOST`, `DEPLOY_USER` e `DEPLOY_SSH_KEY` e o ambiente `producao` no GitHub.

### Backup

```bash
./infra/scripts/backup.sh /var/backups/anuario
```

Para restaurar, em um banco vazio:

```bash
gunzip -c /var/backups/anuario/anuario-AAAAMMDD-HHMMSS.sql.gz | \
  docker compose -f infra/compose.prod.yml --env-file .env exec -T db \
  sh -c 'psql -U "$POSTGRES_USER" "$POSTGRES_DB"'
```

Como os dados vêm só das planilhas versionadas, `migrate` seguido de `importar_anuario` também recria o
banco.

## Publicar uma versão

As versões seguem o [SemVer](https://semver.org/lang/pt-BR/) e são independentes da versão da API. `feat`
sobe a minor, e `fix`, a patch. Detalhes no [ADR 0010](adr/0010-versionamento-e-releases.md).

1. Em um pull request, suba a versão nos quatro arquivos (`frontend/package.json`,
   `frontend/package-lock.json`, `backend/pyproject.toml` e `backend/uv.lock`):

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

O workflow `release.yml` confere a tag, roda o CI completo, publica as imagens
`ghcr.io/yocaslu/projeto-integrador-ii/backend` e `.../frontend` e cria o release. Ele não implanta nada.

## Solução de problemas

| Sintoma | Causa provável | Solução |
| --- | --- | --- |
| API responde 503; painel mostra erro | Nenhuma carga concluída | Rode `migrate` e `importar_anuario` |
| Painel não abre logo após subir | `npm install` ainda em andamento | Acompanhe com `docker compose logs -f frontend` |
| `port is already allocated` | Porta 5173, 8000 ou 5432 em uso | Encerre o outro serviço ou mude a porta em `docker-compose.yml` |
| Importação aborta por hash | Arquivo em `dados/brutos/` diferente do manifesto | Restaure o arquivo (`git checkout -- dados/brutos`) ou, se a versão for nova, registre-a |
| Importação aborta por contagem, localidade ou cabeçalho | Layout da planilha mudou | Use `inspecionar_planilha` e ajuste o mapeamento |
| `relation ... does not exist` | Migrações não aplicadas | Rode `migrate` |
| `DisallowedHost` ou 400 em produção | Domínio fora de `DJANGO_ALLOWED_HOSTS` | Ajuste o `.env` e recrie o `backend` |
| Dados antigos após nova carga | Cache do navegador (até 24 h) | Recarregue sem cache; clientes que usam `ETag` recebem os novos dados |
| Mapa com aviso | Falta `frontend/public/malhas/ufs.json` | Restaure o arquivo ou rode `npm run malha` |
| Testes de ponta a ponta falham em todos os blocos | Dados não importados | Importe antes de rodar o Playwright |
