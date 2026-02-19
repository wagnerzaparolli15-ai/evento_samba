import os
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# CONEXÃO OTIMIZADA COM TRATAMENTO DE STRING (POSTGRES NO RENDER)
uri = os.environ.get('DATABASE_URL')
if uri and uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# MODELO DO BANCO DE DADOS
class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    telefone = db.Column(db.String(20), nullable=False)

# ROTA PRINCIPAL (O QUE ESTAVA DANDO 404)
@app.route('/')
def index():
    return render_template('index.html')

# ROTA DE COMPRA
@app.route('/comprar', methods=['POST'])
def comprar():
    nome = request.form.get('nome')
    telefone = request.form.get('telefone')
    novo_cliente = Cliente(nome=nome, telefone=telefone)
    db.session.add(novo_cliente)
    db.session.commit()
    return "<h1>Reserva confirmada! Entraremos em contato.</h1>"

# PAINEL ADMINISTRATIVO
@app.route('/admin-cara-2026')
def admin():
    clientes = Cliente.query.all()
    return render_template('admin.html', clientes=clientes)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)