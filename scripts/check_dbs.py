import sqlite3, os
files=['fazcomfe.db','instance/fazcomfe.db','database/clientes_evento.db','instance/meu_evento.db']
for f in files:
    if os.path.exists(f):
        try:
            con=sqlite3.connect(f)
            cur=con.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables=[r[0] for r in cur.fetchall()]
            print(f, '->', tables)
            con.close()
        except Exception as e:
            print(f, 'error', e)
    else:
        print(f, 'not found')
