import os, re, mercadopago
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)

# --- CONFIGURAÇÃO DO BANCO DE DADOS ---
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
    pedidos_bar = db.relationship('PedidoBar', backref='comprador', lazy=True)

class Produto(db.Model):
    __tablename__ = 'bar_produtos'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    preco_venda = db.Column(db.Float, nullable=False)
    preco_custo = db.Column(db.Float, default=0.0)
    estoque = db.Column(db.Integer, default=0)
    vendas_count = db.Column(db.Integer, default=0) # Quantos foram vendidos
    imagem_url = db.Column(db.String(500))
    categoria = db.Column(db.String(50)) 
    ativo = db.Column(db.Boolean, default=True)

class PedidoBar(db.Model):
    __tablename__ = 'bar_pedidos'
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'))
    itens_resumo = db.Column(db.Text) 
    valor_total = db.Column(db.Float)
    pago = db.Column(db.Boolean, default=True) # Pix já cai pago
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
        p_id = request.form.get('id')
        p = Produto.query.get(p_id) if p_id else Produto()
        p.nome = request.form.get('nome')
        p.preco_venda = float(request.form.get('preco_venda'))
        p.preco_custo = float(request.form.get('preco_custo'))
        p.estoque = int(request.form.get('estoque'))
        p.imagem_url = request.form.get('imagem_url')
        p.categoria = request.form.get('categoria')
        if not p_id: db.session.add(p)
        db.session.commit()
        return redirect(url_for('admin_bar_produtos'))
    
    produtos = Produto.query.all()
    pedidos_pendentes = PedidoBar.query.filter_by(entregue=False).order_by(PedidoBar.id.desc()).all()
    
    # Contabilidade automática
    faturamento_total = sum(p.valor_total for p in PedidoBar.query.all())
    lucro_total = sum((prod.preco_venda - prod.preco_custo) * prod.vendas_count for prod in produtos)

    return render_template('admin_bar.html', 
                           produtos=produtos, 
                           pedidos=pedidos_pendentes,
                           faturamento=faturamento_total,
                           lucro=lucro_total)

@app.route('/admin/baixa/<int:id>', methods=['POST'])
def baixar_pedido(id):
    pedido = PedidoBar.query.get_or_404(id)
    pedido.entregue = True
    
    # Baixa automática de estoque (Lógica simples por item no resumo)
    # Para cada item no pedido, você deve subtrair manualmente ou via código.
    # Como o resumo é texto, aqui você daria o check no que entregou.
    db.session.commit()
    return redirect(url_for('admin_bar_produtos'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)