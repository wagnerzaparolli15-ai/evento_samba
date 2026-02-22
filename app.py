import os, re, mercadopago
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)

# --- CONFIGURAÇÃO DO BANCO ---
uri = "postgresql://db_fazcomfe_user:bo24NlcJANvGehkj97PytDoNyoiT696V@dpg-d6b4mq4hncsc7386sfag-a/db_fazcomfe?sslmode=require"
app.config['SQLALCHEMY_DATABASE_URI'] = uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
sdk = mercadopago.SDK("APP_USR-3244228687878580-021915-5528b1d97c9055fab65127d73dc1427d-24221819")

# --- MODELOS ---
class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100))
    telefone = db.Column(db.String(20), unique=True)
    pago = db.Column(db.Boolean, default=False)
    utilizado = db.Column(db.Boolean, default=False)

class Produto(db.Model):
    __tablename__ = 'bar_produtos'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    preco_venda = db.Column(db.Float, nullable=False)
    preco_custo = db.Column(db.Float, default=0.0)
    estoque = db.Column(db.Integer, default=0)
    categoria = db.Column(db.String(50))
    imagem_url = db.Column(db.String(500)) # CAMPO PARA LOGOMARCA
    ativo = db.Column(db.Boolean, default=True)

class PedidoBar(db.Model):
    __tablename__ = 'bar_pedidos'
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'))
    itens_resumo = db.Column(db.Text)
    valor_total = db.Column(db.Float)
    entregue = db.Column(db.Boolean, default=False)
    data = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

# --- ROTAS ---
@app.route('/')
def index():
    return render_template('index.html', preco=45.0)

@app.route('/admin/bar/produtos', methods=['GET', 'POST'])
def admin_bar_produtos():
    if request.method == 'POST':
        p = Produto(
            nome=request.form.get('nome'),
            preco_venda=float(request.form.get('preco_venda')),
            preco_custo=float(request.form.get('preco_custo')),
            estoque=int(request.form.get('estoque')),
            imagem_url=request.form.get('imagem_url'), # SALVA A LOGO
            categoria=request.form.get('categoria')
        )
        db.session.add(p)
        db.session.commit()
        return redirect(url_for('admin_bar_produtos'))
    
    produtos = Produto.query.all()
    clientes = Cliente.query.all()
    return render_template('admin_bar.html', produtos=produtos, clientes=clientes)

@app.route('/bar/<int:id>')
def bar(id):
    c = Cliente.query.get_or_404(id)
    produtos = Produto.query.filter_by(ativo=True).all()
    return render_template('bar.html', c=c, produtos=produtos)

@app.route('/checkin/<int:id>')
def checkin(id):
    c = Cliente.query.get_or_404(id)
    c.utilizado = True
    c.pago = True
    db.session.commit()
    return redirect(url_for('admin_bar_produtos'))

@app.route('/admin/reset-total')
def reset_total():
    db.drop_all()
    db.create_all()
    return "<h1>Sistema Resetado com Sucesso! Ingressos, Lucro e Estoque limpos.</h1>"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)