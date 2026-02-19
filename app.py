import os
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# CONFIGURAÇÃO DE CONEXÃO OTIMIZADA
uri = os.environ.get('DATABASE_URL')
if uri and uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)

# Força o uso de SSL para o PostgreSQL profissional do Render
if uri and "sslmode" not in uri and "localhost" not in uri:
    separator = "&" if "?" in uri else "?"
    uri += f"{separator}sslmode=require"

app.config['SQLALCHEMY_DATABASE_URI'] = uri or 'sqlite:///projeto.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# MODELO DO BANCO DE DADOS
class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    telefone = db.Column(db.String(20), nullable=False)

# ROTA DA PÁGINA INICIAL
@app.route('/')
def index():
    return render_template('index.html')

# ROTA DE COMPRA (RESERVA)
@app.route('/comprar', methods=['POST'])
def comprar():
    nome = request.form.get('nome')
    telefone = request.form.get('telefone')
    if nome and telefone:
        novo_cliente = Cliente(nome=nome, telefone=telefone)
        db.session.add(novo_cliente)
        db.session.commit()
        return render_template('obrigado.html', nome=nome)
    return redirect(url_for('index'))

# PAINEL ADMINISTRATIVO (GESTOR DE VENDAS)
@app.route('/admin-cara-2026')
def admin():
    clientes = Cliente.query.all()
    return render_template('admin.html', clientes=clientes)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)