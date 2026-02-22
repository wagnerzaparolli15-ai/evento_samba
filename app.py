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
    utilizado = db.Column(db.Boolean, default=False)
    mp_id = db.Column(db.String(100))
    pedidos_bar = db.relationship('PedidoBar', backref='comprador', lazy=True)

class Produto(db.Model):
    __tablename__ = 'bar_produtos'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    preco = db.Column(db.Float, nullable=False)
    imagem_url = db.Column(db.String(500))
    categoria = db.Column(db.String(50)) # BEBIDAS, COMIDA, LANCHES
    ativo = db.Column(db.Boolean, default=True)

class PedidoBar(db.Model):
    __tablename__ = 'bar_pedidos'
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'))
    itens_resumo = db.Column(db.Text)
    valor_total = db.Column(db.Float)
    pago = db.Column(db.Boolean, default=False)
    entregue = db.Column(db.Boolean, default=False)
    mp_id = db.Column(db.String(100))
    data = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

# --- ROTAS DE INGRESSO ---

@app.route('/')
def index():
    # CORREÇÃO AQUI: Enviando a variável 'preco' que o index.html exige
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
    valor = 45.0 + (c.id / 100.0)
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
    if not c.pago:
        payments = sdk.payment().search({'sort': 'date_created', 'criteria': 'desc'})['response']['results']
        for p in payments:
            if p['status'] == 'approved' and abs(float(p['transaction_amount']) - (45.0 + c.id/100.0)) < 0.01:
                c.pago = True
                db.session.commit()
                break
    if c.pago:
        return redirect(url_for('recepcao', id=c.id))
    return render_template('templates-feedback.html', tipo='aguardando', id=c.id)

@app.route('/recepcao/<int:id>')
def recepcao(id):
    c = Cliente.query.get_or_404(id)
    return render_template('recepcao.html', c=c)

@app.route('/obrigado/<int:id>')
def obrigado(id):
    c = Cliente.query.get_or_404(id)
    checkin_url = url_for('checkin', id=c.id, _external=True)
    return render_template('obrigado.html', nome=c.nome, id_reserva=c.id, checkin_url=checkin_url)

# --- SISTEMA DO BAR ---

@app.route('/bar/<int:id>')
def bar(id):
    c = Cliente.query.get_or_404(id)
    produtos = Produto.query.filter_by(ativo=True).all()
    # Separação por categorias para o layout de abas
    bebidas = [p for p in produtos if p.categoria == 'BEBIDAS']
    comidas = [p for p in produtos if p.categoria == 'COMIDA']
    lanches = [p for p in produtos if p.categoria == 'LANCHES']
    return render_template('bar.html', c=c, bebidas=bebidas, comidas=comidas, lanches=lanches)

@app.route('/bar/gerar_pix', methods=['POST'])
def pix_bar():
    dados = request.json
    pedido = PedidoBar(cliente_id=dados['cliente_id'], itens_resumo=dados['itens'], valor_total=dados['total'])
    db.session.add(pedido); db.session.commit()
    
    pay_data = {
        "transaction_amount": float(dados['total']),
        "description": f"Bar #{pedido.id}",
        "payment_method_id": "pix",
        "payer": {"email": "wagnerzaparolli15@gmail.com"}
    }
    result = sdk.payment().create(pay_data)
    pix = result["response"]["point_of_interaction"]["transaction_data"]
    pedido.mp_id = str(result["response"]["id"]); db.session.commit()
    
    return jsonify({
        "status": "sucesso",
        "pix_img": pix["qr_code_base64"], 
        "pix_copia": pix["qr_code"],
        "pedido_id": pedido.id
    })

# --- ADMINISTRAÇÃO ---

@app.route('/admin/bar/produtos', methods=['GET', 'POST'])
def admin_bar_produtos():
    if request.method == 'POST':
        p_id = request.form.get('id')
        p = Produto.query.get(p_id) if p_id else Produto()
        p.nome = request.form.get('nome')
        p.preco = float(request.form.get('preco'))
        p.imagem_url = request.form.get('imagem_url')
        p.categoria = request.form.get('categoria')
        if not p_id: db.session.add(p)
        db.session.commit()
        return redirect(url_for('admin_bar_produtos'))
    
    produtos = Produto.query.all()
    pedidos_pendentes = PedidoBar.query.filter_by(entregue=False).order_by(PedidoBar.id.desc()).all()
    return render_template('admin_bar.html', produtos=produtos, pedidos=pedidos_pendentes)

@app.route('/admin/baixa/<int:id>', methods=['POST'])
def baixar_pedido(id):
    p = PedidoBar.query.get_or_404(id)
    p.entregue = True
    db.session.commit()
    return redirect(url_for('admin_bar_produtos'))

@app.route('/checkin/<int:id>')
def checkin(id):
    c = Cliente.query.get_or_404(id)
    c.utilizado = True; db.session.commit()
    return render_template('templates-feedback.html', tipo='sucesso', msg=f"BEM-VINDO, {c.nome}!")

@app.route('/admin/reset-total', methods=['POST', 'GET'])
def reset_total():
    db.drop_all()
    db.create_all()
    return "Banco Resetado com Sucesso!"

if __name__ == '__main__':
    # O Render usa a porta 10000 por defeito
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)