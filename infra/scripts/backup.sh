#!/usr/bin/env bash
# Cópia de segurança do banco de produção. Executar na VM, a partir da raiz do repositório.
set -euo pipefail

destino="${1:-/var/backups/anuario}"
mkdir -p "$destino"
arquivo="$destino/anuario-$(date +%Y%m%d-%H%M%S).sql.gz"

docker compose -f infra/compose.prod.yml --env-file .env exec -T db \
  sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' | gzip > "$arquivo"

echo "Backup salvo em $arquivo"
