import os, re, mercadopago
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)

# --- CONFIGURAÇÃO DO BANCO DE DADOS (RENDER) ---
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
    utilizado = db.Column(db.Boolean, default=False) # True se já fez check-in
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
    pago = db.Column(db.Boolean, default=True)
    entregue = db.Column(db.Boolean, default=False)
    data = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

# --- ROTAS DE ACESSO E PORTA ÚNICA ---

@app.route('/')
def index():
    # Envia o preço base do ingresso para o index.html
    return render_template('index.html', preco=45.0)

@app.route('/reservar', methods=['POST'])
def reservar():
    nome = request.form.get('nome', '').upper().strip()
    tel = re.sub(r"\D", "", request.form.get('telefone', ''))
    if not nome or not tel: return "Erro: Nome e telefone obrigatórios."
    
    c = Cliente.query.filter_by(telefone=tel).first()
    if not c:
        c = Cliente(nome=nome, telefone=tel)
        db.session.add(c)
        db.session.commit()
    return redirect(url_for('pagamento', id=c.id))

@app.route('/pagamento/<int:id>')
def pagamento(id):
    c = Cliente.query.get_or_404(id)
    # Valor único para identificar o PIX
    valor = 45.0 + (c.id / 100.0)
    
    pay_data = {
        "transaction_amount": valor,
        "description": f"Ingresso #{c.id} - {c.nome}",
        "payment_method_id": "pix",
        "payer": {"email": "wagnerzaparolli15@gmail.com"}
    }
    result = sdk.payment().create(pay_data)
    
    # Se o Mercado Pago responder ok, gera o QR Code
    if "response" in result and "point_of_interaction" in result["response"]:
        pix = result["response"]["point_of_interaction"]["transaction_data"]
        return render_template('pagamento.html', c=c, pix_codigo=pix["qr_code"], qrcode_base64=pix["qr_code_base64"])
    else:
        return "Erro ao gerar PIX. Tente novamente."

@app.route('/ingresso/<int:id>')
def validar_ingresso(id):
    c = Cliente.query.get_or_404(id)
    
    # Lógica de Redirecionamento Automático
    if c.utilizado: 
        return redirect(url_for('bar', id=c.id)) # JÁ ENTROU -> VAI PRO BAR
    if c.pago: 
        return render_template('recepcao.html', c=c) # JÁ PAGOU -> MOSTRA INGRESSO
    
    # Se não está pago, verifica no Mercado Pago
    payments = sdk.payment().search({'sort': 'date_created', 'criteria': 'desc'})['response']['results']
    for p in payments:
        if p['status'] == 'approved' and abs(float(p['transaction_amount']) - (45.0 + c.id/100.0)) < 0.01:
            c.pago = True
            db.session.commit()
            return render_template('recepcao.html', c=c)
            
    return redirect(url_for('pagamento', id=c.id))

# --- SISTEMA DO BAR ---

@app.route('/bar/<int:id>')
def bar(id):
    c = Cliente.query.get_or_404(id)
    produtos = Produto.query.filter_by(ativo=True).all()
    bebidas = [p for p in produtos if p.categoria == 'BEBIDAS']
    comidas = [p for p in produtos if p.categoria == 'COMIDA']
    return render_template('bar.html', c=c, bebidas=bebidas, comidas=comidas)

# --- ADMINISTRAÇÃO E FINANCEIRO ---

@app.route('/admin/bar/produtos', methods=['GET', 'POST'])
def admin_bar_produtos():
    if request.method == 'POST':
        p_id = request.form.get('id')
        p = Produto.query.get(p_id) if p_id else Produto()
        p.nome = request.form.get('nome')
        p.preco_venda = float(request.form.get('preco_venda'))
        p.preco_custo = float(request.form.get('preco_custo'))
        p.estoque = int(request.form.get('estoque'))
        p.categoria = request.form.get('categoria')
        p.imagem_url = request.form.get('imagem_url')
        if not p_id: db.session.add(p)
        db.session.commit()
        return redirect(url_for('admin_bar_produtos'))
    
    produtos = Produto.query.all()
    pedidos = PedidoBar.query.filter_by(entregue=False).all()
    
    # Contabilidade automática
    faturamento = sum(ped.valor_total for ped in PedidoBar.query.all())
    # O lucro é calculado sobre os pedidos entregues (exemplo simplificado)
    lucro = faturamento * 0.4 
    
    return render_template('admin_bar.html', produtos=produtos, pedidos=pedidos, faturamento=faturamento, lucro=lucro)

@app.route('/checkin/<int:id>')
def checkin(id):
    c = Cliente.query.get_or_404(id)
    c.utilizado = True # Ativa a trava do Bar
    db.session.commit()
    return f"<h1>Check-in realizado: {c.nome} liberado para o BAR!</h1>"

@app.route('/admin/reset-total')
def reset_total():
    db.drop_all()
    db.create_all()
    return "Banco de dados resetado com sucesso!"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)