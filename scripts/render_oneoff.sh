#!/usr/bin/env bash
set -euo pipefail

echo "=== Render one-off helper: backup -> check duplicates -> migrate ==="

echo "BASE_URL=${BASE_URL:-<not-set>}"
echo "SECRET_KEY=${SECRET_KEY:-<not-set>}"
echo "DATABASE_URL=${DATABASE_URL:-<not-set>}"

read -p "1) Fazer backup do banco (recomendado). Tentar pg_dump agora? (y/N) " -r
if [[ $REPLY =~ ^[Yy]$ ]]; then
  if command -v pg_dump >/dev/null 2>&1; then
    BACKUP_FILE="backup_$(date +%Y%m%d%H%M).dump"
    echo "Executando pg_dump... file=$BACKUP_FILE"
    pg_dump "$DATABASE_URL" -Fc -f "$BACKUP_FILE"
    echo "Backup salvo em $BACKUP_FILE"
  else
    echo "pg_dump não encontrado — por favor faça backup via painel do Render." >&2
  fi
else
  echo "Pulando backup. Você confirmou que já possui backup?" 
fi

echo
echo "2) Listar duplicatas (dry-run)"
python scripts/clean_duplicates.py || echo "Erro ao rodar clean_duplicates.py"

read -p "Remover duplicatas automaticamente (mantendo menor id)? (y/N) " -r
if [[ $REPLY =~ ^[Yy]$ ]]; then
  echo "Executando remoção de duplicatas..."
  python scripts/clean_duplicates.py --apply
  echo "Remoção concluída."
else
  echo "Pulando remoção de duplicatas."
fi

echo
echo "3) Aplicar migrações (flask db upgrade)"
export FLASK_APP=app.py
flask db upgrade

echo
echo "Migrações aplicadas. Faça um teste de compra no site para verificar QR e /admin."
echo "Se quiser inspecionar logs: veja o painel do Render ou use 'logs' no CLI do Render."

exit 0
