import os, re, mercadopago
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)

# --- CONFIGURAÇÃO DO BANCO DE DADOS (POSTGRESQL RENDER) ---
uri = "postgresql://db_fazcomfe_user:bo24NlcJANvGehkj97PytDoNyoiT696V@dpg-d6b4mq4hncsc7386sfag-a/db_fazcomfe?sslmode=require"
app.config['SQLALCHEMY_DATABASE_URI'] = uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {"pool_pre_ping": True, "pool_recycle": 300}

db = SQLAlchemy(app)
sdk = mercadopago.SDK("APP_USR-3244228687878580-021915-5528b1d97c9055fab65127d73dc1427d-24221819")

# --- MODELOS ---
class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100))
    telefone = db.Column(db.String(20), unique=True)
    pago = db.Column(db.Boolean, default=False)
    utilizado = db.Column(db.Boolean, default=False)
    pedidos_bar = db.relationship('PedidoBar', backref='comprador', lazy=True)

class Produto(db.Model):
    __tablename__ = 'bar_produtos'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    preco_venda = db.Column(db.Float, nullable=False)
    preco_custo = db.Column(db.Float, default=0.0)
    estoque = db.Column(db.Integer, default=0)
    categoria = db.Column(db.String(50)) # BEBIDAS ou COMIDA
    imagem_url = db.Column(db.String(500))
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

# --- ROTAS DE VENDA DE INGRESSO ---

@app.route('/')
def index():
    return render_template('index.html', preco=45.0)

@app.route('/reservar', methods=['POST'])
def reservar():
    nome = request.form.get('nome', '').upper().strip()
    tel = re.sub(r"\D", "", request.form.get('telefone', ''))
    if not nome or not tel: return "Erro: Preencha todos os campos."
    
    c = Cliente.query.filter_by(telefone=tel).first()
    if not c:
        c = Cliente(nome=nome, telefone=tel)
        db.session.add(c)
        db.session.commit()
    return redirect(url_for('pagamento', id=c.id))

@app.route('/pagamento/<int:id>')
def pagamento(id):
    c = Cliente.query.get_or_404(id)
    if c.pago: return redirect(url_for('validar_ingresso', id=c.id))
    
    valor = round(45.0 + (c.id / 100.0), 2)
    pay_data = {
        "transaction_amount": valor,
        "description": f"Ingresso #{c.id} - {c.nome}",
        "payment_method_id": "pix",
        "payer": {"email": "wagnerzaparolli15@gmail.com"}
    }
    result = sdk.payment().create(pay_data)
    pix = result["response"]["point_of_interaction"]["transaction_data"]
    return render_template('pagamento.html', c=c, pix_codigo=pix["qr_code"], qrcode_base64=pix["qr_code_base64"])

@app.route('/ingresso/<int:id>')
def validar_ingresso(id):
    c = Cliente.query.get_or_404(id)
    
    # 1. Se já deu Check-in na porta, vai direto pro BAR
    if c.utilizado:
        return redirect(url_for('bar', id=c.id))
    
    # 2. Se já pagou mas não entrou, mostra a RECEPÇÃO
    if c.pago:
        return render_template('recepcao.html', c=c)
    
    # 3. Se não pagou no banco, tenta validar no Mercado Pago
    valor_procurado = round(45.0 + (c.id / 100.0), 2)
    payments = sdk.payment().search({'sort': 'date_created', 'criteria': 'desc'})['response']['results']
    for p in payments:
        if p['status'] == 'approved' and abs(float(p['transaction_amount']) - valor_procurado) < 0.05:
            c.pago = True
            db.session.commit()
            return render_template('recepcao.html', c=c)
            
    # 4. Se clicar e não confirmou ainda, mostra a tela de "Aguardando" (templates-feedback.html)
    return render_template('templates-feedback.html', tipo='aguardando', id=c.id)

# --- ROTAS DO BAR ---

@app.route('/bar/<int:id>')
def bar(id):
    c = Cliente.query.get_or_404(id)
    # Proteção: só acessa o bar quem já teve o check-in feito (utilizado=True)
    if not c.utilizado:
        return redirect(url_for('validar_ingresso', id=c.id))
        
    produtos = Produto.query.filter_by(ativo=True).all()
    return render_template('bar.html', c=c, produtos=produtos)

# --- ROTAS DE ADMINISTRAÇÃO (PAINEL DO CARA) ---

@app.route('/admin/bar/produtos', methods=['GET', 'POST'])
def admin_bar_produtos():
    if request.method == 'POST':
        p = Produto(
            nome=request.form.get('nome'),
            preco_venda=float(request.form.get('preco_venda')),
            preco_custo=float(request.form.get('preco_custo')),
            estoque=int(request.form.get('estoque')),
            categoria=request.form.get('categoria')
        )
        db.session.add(p)
        db.session.commit()
        return redirect(url_for('admin_bar_produtos'))
    
    produtos = Produto.query.all()
    clientes = Cliente.query.all()
    pedidos = PedidoBar.query.all()
    
    faturamento = sum(ped.valor_total for ped in pedidos)
    # Cálculo de lucro baseado na margem de cada produto vendido
    lucro = sum((p.preco_venda - p.preco_custo) for p in produtos) # Exemplo básico
    
    return render_template('admin_bar.html', produtos=produtos, clientes=clientes, faturamento=faturamento, lucro=lucro)

@app.route('/checkin/<int:id>')
def checkin(id):
    c = Cliente.query.get_or_404(id)
    c.utilizado = True
    c.pago = True # Garante que está liberado
    db.session.commit()
    return redirect(url_for('admin_bar_produtos'))

@app.route('/admin/reset-total', methods=['GET'])
def reset_total():
    db.drop_all()
    db.create_all()
    return "<h1>Sistema Resetado com Sucesso! Ingressos, Lucro e Estoque limpos.</h1>"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)