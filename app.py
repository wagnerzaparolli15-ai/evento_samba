import os
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)

# Configuração do Banco de Dados Profissional (PostgreSQL no Render)
# Se não encontrar a variável, ele usa um banco local para testes
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///projeto.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Modelo de Dados para os Clientes do Evento CARA 2026
class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    telefone = db.Column(db.String(20), nullable=False)
    data_inscricao = db.Column(db.DateTime, default=datetime.utcnow)

# Criar as tabelas no banco de dados
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/comprar', methods=['POST'])
def comprar():
    nome = request.form.get('nome')
    telefone = request.form.get('telefone')
    
    if nome and telefone:
        novo_cliente = Cliente(nome=nome, telefone=telefone)
        db.session.add(novo_cliente)
        db.session.commit()
        return redirect(url_for('obrigado'))
    return redirect(url_for('index'))

@app.route('/obrigado')
def obrigado():
    return render_template('obrigado.html')

# PAINEL DE GESTÃO - ACESSO EXCLUSIVO DO PRODUTOR
@app.route('/admin-cara-2026')
def admin():
    # Busca todos os clientes que compraram ingressos, do mais recente para o mais antigo
    lista_clientes = Cliente.query.order_by(Cliente.id.desc()).all()
    return render_template('admin.html', clientes=lista_clientes)

if __name__ == '__main__':
    app.run(debug=True)