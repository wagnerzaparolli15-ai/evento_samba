#!/usr/bin/env bash
set -euo pipefail

# Script automatizado para Plano Free (Sem Shell interativo)
export FLASK_APP=app.py

echo "=== Iniciando processo de limpeza e migração ==="

# Tenta limpar duplicatas automaticamente. 
# O "|| true" garante que, se der erro (ex: pasta errada), o site não morra.
python scripts/clean_duplicates.py --apply || python clean_duplicates.py --apply || echo "Aviso: Script de duplicatas não encontrado."

echo "=== Aplicando migrações (flask db upgrade) ==="
# Isso cria a coluna 'valor_pago' que está faltando no banco
flask db upgrade

echo "=== Inicialização concluída. Ligando o site... ==="