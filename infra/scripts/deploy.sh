#!/usr/bin/env bash
# Implantação na VM, chamada pelo workflow deploy.yml.
# Variáveis: DEPLOY_HOST, DEPLOY_USER, DEPLOY_SSH_KEY e TAG.
set -euo pipefail

: "${DEPLOY_HOST:?defina DEPLOY_HOST}"
: "${DEPLOY_USER:?defina DEPLOY_USER}"
: "${DEPLOY_SSH_KEY:?defina DEPLOY_SSH_KEY}"
: "${TAG:?defina TAG}"

DIRETORIO_REMOTO="/opt/anuario"

chave="$(mktemp)"
trap 'rm -f "$chave"' EXIT
printf '%s\n' "$DEPLOY_SSH_KEY" > "$chave"
chmod 600 "$chave"

ssh -i "$chave" -o StrictHostKeyChecking=accept-new "$DEPLOY_USER@$DEPLOY_HOST" bash -s <<EOF
set -euo pipefail
cd "$DIRETORIO_REMOTO"
git pull --ff-only
export TAG="$TAG"
docker compose -f infra/compose.prod.yml --env-file .env pull
docker compose -f infra/compose.prod.yml --env-file .env up -d
docker compose -f infra/compose.prod.yml --env-file .env exec -T backend \
  uv run --no-dev python manage.py migrate --noinput
EOF
