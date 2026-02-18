@echo off
echo =========================================
echo REORGANIZANDO SISTEMA COMPLETAMENTE
echo =========================================

REM Criar pastas se nao existirem
if not exist templates mkdir templates
if not exist database mkdir database

echo Criando app.py...

(
echo from flask import Flask, render_template, request, redirect
echo import sqlite3
echo import os
echo.
echo app = Flask(__name__)
echo.
echo DATABASE = os.path.join("database", "clientes_evento.db")
echo.
echo def criar_tabela():
echo^    conn = sqlite3.connect(DATABASE)
echo^    cursor = conn.cursor()
echo^    cursor.execute("""
echo^        CREATE TABLE IF NOT EXISTS clientes (
echo^            id INTEGER PRIMARY KEY AUTOINCREMENT,
echo^            nome TEXT,
echo^            telefone TEXT
echo^        )
echo^    """)
echo^    conn.commit()
echo^    conn.close()
echo.
echo criar_tabela()
echo.
echo @app.route("/")
echo def index():
echo^    return render_template("index.html")
echo.
echo @app.route("/cadastrar", methods=["POST"])
echo def cadastrar():
echo^    nome = request.form.get("nome")
echo^    telefone = request.form.get("telefone")
echo.
echo^    conn = sqlite3.connect(DATABASE)
echo^    cursor = conn.cursor()
echo^    cursor.execute("INSERT INTO clientes (nome, telefone) VALUES (?, ?)", (nome, telefone))
echo^    conn.commit()
echo^    conn.close()
echo.
echo^    return redirect("/")
echo.
echo @app.route("/admin")
echo def admin():
echo^    conn = sqlite3.connect(DATABASE)
echo^    cursor = conn.cursor()
echo^    cursor.execute("SELECT * FROM clientes ORDER BY id DESC")
echo^    clientes = cursor.fetchall()
echo^    conn.close()
echo^    return render_template("admin.html", clientes=clientes)
echo.
echo if __name__ == "__main__":
echo^    app.run(debug=True)
) > app.py

echo Criando templates...

(
echo ^<!DOCTYPE html^>
echo ^<html^>
echo ^<head^>
echo ^<meta charset="UTF-8"^>
echo ^<title^>Cadastro Evento^</title^>
echo ^</head^>
echo ^<body^>
echo ^<h1^>Cadastro Evento^</h1^>
echo ^<form action="/cadastrar" method="POST"^>
echo Nome:^<br^>
echo ^<input type="text" name="nome" required^>^<br^>^<br^>
echo Telefone:^<br^>
echo ^<input type="text" name="telefone" required^>^<br^>^<br^>
echo ^<button type="submit"^>Cadastrar^</button^>
echo ^</form^>
echo ^<br^>
echo ^<a href="/admin"^>Ver Admin^</a^>
echo ^</body^>
echo ^</html^>
) > templates\index.html

(
echo ^<!DOCTYPE html^>
echo ^<html^>
echo ^<head^>
echo ^<title^>Admin^</title^>
echo ^</head^>
echo ^<body^>
echo ^<h1^>Lista de Clientes^</h1^>
echo ^<table border="1"^>
echo ^<tr^>^<th^>ID^</th^>^<th^>Nome^</th^>^<th^>Telefone^</th^>^</tr^>
echo ^{%% for cliente in clientes %%^}
echo ^<tr^>
echo ^<td^>^{{ cliente[0] }}^</td^>
echo ^<td^>^{{ cliente[1] }}^</td^>
echo ^<td^>^{{ cliente[2] }}^</td^>
echo ^</tr^>
echo ^{%% endfor %%^}
echo ^</table^>
echo ^<br^>
echo ^<a href="/"^>Voltar^</a^>
echo ^</body^>
echo ^</html^>
) > templates\admin.html

echo.
echo
