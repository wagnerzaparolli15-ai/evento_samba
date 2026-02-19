#!/usr/bin/env bash
set -euo pipefail

# Script seguro para rodar em uma shell one-off no Render.
# Uso: cole este arquivo no servidor ou execute diretamente na shell do one-off.

export FLASK_APP=app.py

echo "=== Dry-run: listando duplicatas ==="
python scripts/clean_duplicates.py || { echo "Dry-run falhou"; exit 1; }

read -p "Deseja aplicar as remoções e executar migrações? (digite 'yes' para confirmar) " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
  echo "Abortando por segurança. Nenhuma alteração aplicada."
  exit 0
fi

echo "=== Aplicando remoções ==="
python scripts/clean_duplicates.py --apply

echo "=== Aplicando migrações (flask db upgrade) ==="
flask db upgrade

echo "Pronto. Verifique a aplicação e rode os testes de fumaça no navegador."
