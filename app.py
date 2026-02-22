import os, re, mercadopago
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
uri = "postgresql://db_fazcomfe_user:bo24NlcJANvGehkj97PytDoNyoiT696V@dpg-d6b4mq4hncsc7386sfag-a/db_fazcomfe?sslmode=require"
app.config['SQLALCHEMY_DATABASE_URI'] = uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
sdk = mercadopago.SDK("APP_USR-3244228687878580-021915-5528b1d97c9055fab65127d73dc1427d-24221819")

class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100))
    telefone = db.Column(db.String(20), unique=True)
    pago = db.Column(db.Boolean, default=False)
    utilizado = db.Column(db.Boolean, default=False) # CAMPO CHAVE
    pedidos_bar = db.relationship('PedidoBar', backref='comprador', lazy=True)

class Produto(db.Model):
    __tablename__ = 'bar_produtos'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    preco_venda = db.Column(db.Float, nullable=False)
    preco_custo = db.Column(db.Float, default=0.0)
    estoque = db.Column(db.Integer, default=0)
    categoria = db.Column(db.String(50)) 
    ativo = db.Column(db.Boolean, default=True)

class PedidoBar(db.Model):
    __tablename__ = 'bar_pedidos'
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'))
    itens_resumo = db.Column(db.Text) 
    valor_total = db.Column(db.Float)
    entregue = db.Column(db.Boolean, default=False)
    data = db.Column(db.DateTime, default=datetime.utcnow)

@app.route('/')
def index():
    return render_template('index.html', preco=45.0)

@app.route('/ingresso/<int:id>')
def validar_ingresso(id):
    c = Cliente.query.get_or_404(id)
    if c.utilizado: # Se deu baixa, link vira BAR
        return redirect(url_for('bar', id=c.id))
    if c.pago: # Se pagou mas não entrou, mostra ingresso
        return render_template('recepcao.html', c=c)
    
    # Lógica de checagem do MP (simplificada para o exemplo)
    return render_template('templates-feedback.html', tipo='aguardando', id=c.id)

@app.route('/bar/<int:id>')
def bar(id):
    c = Cliente.query.get_or_404(id)
    produtos = Produto.query.filter_by(ativo=True).all()
    # Separação por categorias
    bebidas = [p for p in produtos if p.categoria == 'BEBIDAS']
    comidas = [p for p in produtos if p.categoria == 'COMIDA']
    return render_template('bar.html', c=c, bebidas=bebidas, comidas=comidas)

@app.route('/checkin/<int:id>')
def checkin(id):
    c = Cliente.query.get_or_404(id)
    c.utilizado = True # AQUI É O PULO DO GATO
    db.session.commit()
    return render_template('templates-feedback.html', tipo='sucesso', msg=f"BEM-VINDO AO EVENTO, {c.nome}!")

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)