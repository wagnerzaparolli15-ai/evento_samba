#!/usr/bin/env python3
"""Script seguro para identificar e (opcionalmente) remover telefones duplicados.

Uso:
  # Execução em modo dry-run (apenas lista)
  python scripts/clean_duplicates.py

  # Para aplicar as remoções (mantém o registro com menor id)
  python scripts/clean_duplicates.py --apply

O script conecta usando `DATABASE_URL` do ambiente (ou sqlite local `fazcomfe.db`).
"""
import os
import sqlite3
from collections import defaultdict
from sqlalchemy import create_engine, text


def get_engine():
    uri = os.environ.get('DATABASE_URL')
    if uri:
        if uri.startswith('postgres://'):
            uri = uri.replace('postgres://', 'postgresql://', 1)
        return create_engine(uri)

    # Se não há DATABASE_URL, tente detectar um DB sqlite que contenha a tabela `cliente`.
    candidates = ['instance/fazcomfe.db', 'instance/meu_evento.db', 'database/clientes_evento.db', 'fazcomfe.db']
    for c in candidates:
        path = os.path.join(os.getcwd(), c)
        if os.path.exists(path):
            try:
                con = sqlite3.connect(path)
                cur = con.cursor()
                cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cliente'")
                if cur.fetchone():
                    con.close()
                    return create_engine(f"sqlite:///{path}")
                con.close()
            except Exception:
                continue

    # fallback
    return create_engine('sqlite:///fazcomfe.db')


def find_duplicates(engine):
    sql = text("SELECT id, nome, telefone FROM cliente ORDER BY telefone, id")
    with engine.connect() as conn:
        rows = conn.execute(sql).fetchall()
    groups = defaultdict(list)
    for r in rows:
        tel = r[2]
        groups[tel].append((r[0], r[1]))
    dupes = {tel: items for tel, items in groups.items() if len(items) > 1}
    return dupes


def main():
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument('--apply', action='store_true', help='Remover duplicatas (mantém menor id)')
    args = p.parse_args()

    engine = get_engine()
    dupes = find_duplicates(engine)
    if not dupes:
        print('Nenhuma duplicata encontrada.')
        return

    print('Telefones duplicados encontrados:')
    for tel, items in dupes.items():
        print(f'- {tel}:')
        for id_, nome in items:
            print(f'    id={id_} nome={nome}')

    if args.apply:
        print('\nAplicando remoção: mantendo o menor id por telefone...')
        for tel, items in dupes.items():
            items_sorted = sorted(items, key=lambda x: x[0])
            keep_id = items_sorted[0][0]
            remove_ids = [str(i[0]) for i in items_sorted[1:]]
            if remove_ids:
                sql = text(f"DELETE FROM cliente WHERE id IN ({','.join(remove_ids)})")
                with engine.begin() as conn:
                    conn.execute(sql)
                print(f'  Removidos ids {remove_ids} (telefone {tel}), mantido id {keep_id}')
        print('Remoção concluída.')
    else:
        print('\nRode com --apply para remover automaticamente as duplicatas (mantendo menor id).')


if __name__ == '__main__':
    main()
