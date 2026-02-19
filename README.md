# Evento Samba — Guia rápido de otimização e deploy

Objetivo: rodar localmente (SQLite) e em produção no Render (Postgres), mantendo QR funcional.

Passos principais:

1) Dependências
- Instale no venv:

```powershell
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2) Variáveis de ambiente no Render
- `DATABASE_URL` — URL do Postgres (Render fornece).
- `SECRET_KEY` — string aleatória.
- `BASE_URL` — (opcional) `https://seu-dominio.onrender.com` para construir QR com domínio fixo.

3) Migrações (recomendado)
- Instalado `Flask-Migrate`.
- Com `FLASK_APP=app.py` configurado, execute:

```bash
flask db init      # apenas uma vez
flask db migrate -m "Initial"
flask db upgrade
```

Se preferir não usar migrações, crie tabelas direto (one-off no Render):

```bash
python -c "from app import db; db.create_all()"
```

4) Comportamento do app
- `app.py` agora normaliza telefones (apenas dígitos) e impede duplicação (coluna `telefone` com `unique=True`).
- Em caso de duplicata, usuário recebe mensagem amigável no `index`.
- A URL do QR (`checkin_url`) é construída a partir de `BASE_URL` quando definida; caso contrário usa o host da requisição — assim funciona local e em produção.

5) Procfile para o Render

```
web: gunicorn app:app --log-file -
```

6) Testes rápidos locais
- Inicie app:

```powershell
venv\Scripts\python.exe app.py
```

- Acesse `http://127.0.0.1:5000`, compre um ingresso e verifique QR na página de obrigado.

Se quiser, eu posso:
- Gerar a pasta `migrations/` local com `flask db init/migrate` executados aqui (opção A).
- Criar um `smoke-test` automatizado que verifica compra e /admin (opção C).

Responda com qual opção prefere (A, C, ou ambos).