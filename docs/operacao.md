# Instalação e operação

Como colocar a aplicação no ar, carregar os dados e mantê-la. Todos os comandos rodam a partir da
raiz do repositório.

## 1. Requisitos

- Docker com o plugin Compose (Docker Desktop no Windows e no macOS).
- Git.
- Cerca de 2 GB livres para as imagens e o banco.

Não é preciso instalar Python, Node.js nem PostgreSQL: tudo roda em containers.

## 2. Ambiente local

```bash
git clone https://github.com/yocaslu/projeto-integrador-ii.git
cd projeto-integrador-ii
cp .env.example .env
docker compose up -d --build
docker compose exec backend uv run python manage.py migrate
docker compose exec backend uv run python manage.py importar_anuario
```

| Serviço | Endereço |
| --- | --- |
| Painel | <http://localhost:5173> |
| API | <http://localhost:8000/api/v1/> |
| Documentação interativa da API (Swagger UI) | <http://localhost:8000/api/v1/docs/> |
| Documentação da API (ReDoc) | <http://localhost:8000/api/v1/redoc/> |

Na primeira subida, o serviço do painel instala as dependências do Node antes de iniciar; espere
um ou dois minutos até <http://localhost:5173> responder (`docker compose logs -f frontend`).

O banco e a API aceitam conexões só do próprio computador. O painel, que repassa as chamadas
`/api` à API, fica acessível na rede local, em `http://<ip-do-computador>:5173`.

| Tarefa | Comando |
| --- | --- |
| Parar | `docker compose stop` |
| Subir de novo | `docker compose up -d` |
| Ver os logs | `docker compose logs -f backend` (ou `frontend`, `db`) |
| Apagar tudo, inclusive o banco | `docker compose down -v` |

## 3. Importar os dados

```bash
docker compose exec backend uv run python manage.py importar_anuario
```

O comando:

1. confere o SHA-256 de cada arquivo de `dados/brutos/` contra a tabela de
   [`dados/README.md`](../dados/README.md) e aborta se algum divergir;
2. lê as planilhas do Anuário (edições de 2024, 2025 e 2026) e a população do IBGE;
3. calcula os totais regionais que o Anuário não publica, como soma das UFs;
4. grava tudo numa única transação: se algo falhar, nada é gravado;
5. gera o relatório de validação em `dados/relatorios/`.

Saída esperada:

```text
Carga 764af7ef35c3 concluída: 3498 registros (460 regionais calculados) e 462 populações.
  divergencia: 0
  aviso: 0
  informacao: 1557
Nenhuma divergência acima da tolerância.
```

Rodar de novo é seguro: não duplica registros nem muda os identificadores. Antes da primeira
importação, a API responde 503 em todos os recursos de dados e o painel mostra o erro.

| Opção | Efeito |
| --- | --- |
| `--somente-validar` | Lê, confere e gera o relatório sem gravar nada no banco. |
| `--estrito` | Termina com erro se o relatório tiver alguma divergência. |
| `--dados DIR` | Lê os arquivos de outro diretório. |
| `--relatorio DIR` | Grava o relatório em outro diretório. |
| `--manifesto ARQUIVO` | Usa outra tabela de hashes. |

### O relatório de validação

`dados/relatorios/validacao-<versao>.md` resume e `validacao-<versao>.csv` lista, um por linha, os
apontamentos de três níveis:

- **divergência:** a taxa calculada com a população do IBGE, a variação ou a participação diferem
  do que o FBSP publicou em mais de 1e-6. Deve ser zero;
- **aviso:** célula vazia na planilha ou registro do banco que não veio da planilha atual;
- **informação:** fatos esperados, como totais regionais calculados ou somas parciais publicadas
  pelo FBSP.

## 4. Atualizar os dados

### Nova edição do Anuário

Uma edição nova costuma mudar a posição das tabelas e dos cabeçalhos, então exige ajuste no código
de importação (veja [importacao.md](importacao.md)). O roteiro:

1. Copie a planilha para `dados/brutos/` com um nome novo (`anuario-2027.xlsx`); nunca sobrescreva
   um arquivo existente.
2. Calcule o hash (`sha256sum dados/brutos/anuario-2027.xlsx`) e acrescente a linha na tabela de
   `dados/README.md`.
3. Veja como a planilha está organizada:
   `docker compose exec backend uv run python manage.py inspecionar_planilha T02 T03 T08`.
4. Ajuste `backend/apps/importacao/mapeamento.py` e a contagem esperada, e confira com
   `importar_anuario --somente-validar --estrito`.
5. Importe e abra um pull request com os arquivos, o mapeamento e os testes.

### Nova estimativa de população do IBGE

Mesmo caminho: arquivo novo em `dados/brutos/`, hash em `dados/README.md`, leitura em
`backend/apps/importacao/leitores/ibge.py` se o formato mudar.

### Malha do mapa

A malha das UFs fica em `frontend/public/malhas/ufs.json`. Para baixá-la de novo do IBGE:
`cd frontend && npm run malha` ([frontend/public/README.md](../frontend/public/README.md)).

## 5. Produção

A produção roda numa máquina virtual Ubuntu Server com Docker, atrás do Traefik, que obtém o
certificado HTTPS do Let's Encrypt e roteia o domínio: `/api` vai para o backend (Gunicorn) e o
resto para o painel (Nginx). As imagens são as publicadas em cada versão no GitHub Container
Registry (`ghcr.io/yocaslu/projeto-integrador-ii/backend` e `.../frontend`).

### Primeira instalação

Na VM, com um domínio apontando para o IP dela e as portas 80 e 443 abertas:

```bash
sudo git clone https://github.com/yocaslu/projeto-integrador-ii.git /opt/anuario
cd /opt/anuario
cp .env.example .env
```

Edite o `.env`:

| Variável | Valor em produção |
| --- | --- |
| `DJANGO_SECRET_KEY` | Uma chave longa e aleatória (`python3 -c "import secrets; print(secrets.token_urlsafe(50))"`). |
| `DJANGO_ALLOWED_HOSTS` | O domínio, por exemplo `anuario.exemplo.org`. |
| `POSTGRES_PASSWORD` | Uma senha forte. |
| `POSTGRES_HOST` | `db` (o padrão). |
| `DOMINIO` | O domínio público. |
| `ACME_EMAIL` | E-mail para os avisos do Let's Encrypt. |

`DJANGO_SETTINGS_MODULE` não precisa mudar: o Compose de produção já usa `config.settings.prod`.

Suba a versão desejada, crie as tabelas e importe:

```bash
export TAG=1.4.0   # versão publicada; sem TAG, usa latest
docker compose -f infra/compose.prod.yml --env-file .env up -d
docker compose -f infra/compose.prod.yml --env-file .env exec -T backend uv run --no-dev python manage.py migrate --noinput
docker compose -f infra/compose.prod.yml --env-file .env exec -T backend uv run --no-dev python manage.py importar_anuario
```

As imagens não contêm os dados: as planilhas vêm de `dados/brutos/` do clone, montado no
container. Por isso a importação precisa ser repetida depois de atualizar o clone com dados novos.

### Atualizar para uma nova versão

Pelo GitHub: o workflow **Deploy** (Actions → Deploy → Run workflow) constrói as imagens do commit
atual, entra na VM por SSH, atualiza o clone, sobe os containers e aplica as migrações. Ele usa os
segredos `DEPLOY_HOST`, `DEPLOY_USER` e `DEPLOY_SSH_KEY` do ambiente `producao`.

Manualmente, na VM:

```bash
cd /opt/anuario && git pull --ff-only
export TAG=X.Y.Z
docker compose -f infra/compose.prod.yml --env-file .env pull
docker compose -f infra/compose.prod.yml --env-file .env up -d
docker compose -f infra/compose.prod.yml --env-file .env exec -T backend uv run --no-dev python manage.py migrate --noinput
```

Se a versão trouxer dados novos (veja as notas do release), rode também o `importar_anuario`.

### Cópia de segurança

```bash
infra/scripts/backup.sh                 # grava em /var/backups/anuario
infra/scripts/backup.sh /outro/destino
```

Para restaurar num banco vazio:

```bash
gunzip -c /var/backups/anuario/anuario-AAAAMMDD-HHMMSS.sql.gz | \
  docker compose -f infra/compose.prod.yml --env-file .env exec -T db \
  sh -c 'psql -U "$POSTGRES_USER" "$POSTGRES_DB"'
```

Como todo o conteúdo do banco vem de arquivos versionados, também é possível reconstruí-lo do zero
com `migrate` e `importar_anuario`.

## 6. Problemas comuns

| Sintoma | O que fazer |
| --- | --- |
| A API responde 503 e o painel mostra erro | Ainda não há carga concluída: rode `importar_anuario`. |
| `importar_anuario` aborta com hash divergente | Um arquivo de `dados/brutos/` foi alterado ou substituído. Restaure-o com `git checkout -- dados/brutos/` ou registre o novo hash (seção 4). |
| `importar_anuario` aborta por contagem ou cabeçalho | A planilha mudou de formato. Rode `inspecionar_planilha` e ajuste o mapeamento (seção 4). |
| `Bad Request (400)` em todas as páginas da API em produção | O domínio não está em `DJANGO_ALLOWED_HOSTS`. |
| Porta 5432, 8000 ou 5173 em uso | Outro programa usa a porta; pare-o ou mude o mapeamento de portas no `docker-compose.yml`. |
| O painel não abre logo depois de `up` | O serviço ainda está instalando as dependências; acompanhe com `docker compose logs -f frontend`. |
| "Não foi possível exibir o mapa" | Falta `frontend/public/malhas/ufs.json`; gere com `npm run malha`. |
| Mudou o `.env` e nada aconteceu | Recrie os containers: `docker compose up -d --force-recreate`. |
