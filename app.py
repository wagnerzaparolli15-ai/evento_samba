import os, mercadopago, qrcode, io, base64
from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func

app = Flask(__name__)

# --- CONFIGURAÇÃO ---
db_url = os.getenv("DATABASE_URL")
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url or "sqlite:///bafafa_2026.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.getenv("SECRET_KEY", "BAFAFA_MASTER_2026_ENTERPRISE")

db = SQLAlchemy(app)
sdk = mercadopago.SDK(os.getenv("MP_ACCESS_TOKEN"))

# --- MODELAGEM (RESPEITANDO A LÓGICA ATUAL) ---
class Equipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100)); usuario = db.Column(db.String(50), unique=True)
    senha = db.Column(db.String(50)); cargo = db.Column(db.String(30))
    caixinha_total = db.Column(db.Float, default=0.0)

class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100)); telefone = db.Column(db.String(20))
    pago = db.Column(db.Boolean, default=False); na_casa = db.Column(db.Boolean, default=False)
    valor_total = db.Column(db.Float, default=45.0)
    mp_id = db.Column(db.String(100))

class CustoOperacional(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(100)); valor = db.Column(db.Float)

class Produto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100)); preco_venda = db.Column(db.Float)
    preco_custo = db.Column(db.Float); estoque = db.Column(db.Integer, default=0)
    imagem_url = db.Column(db.String(500))

class Pedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'))
    produto_id = db.Column(db.Integer, db.ForeignKey('produto.id'))
    status = db.Column(db.String(20), default='No Carrinho')
    metodo_pagamento = db.Column(db.String(50))

# --- AUXILIARES ---
def gerar_qr_b64(conteudo):
    qr = qrcode.make(conteudo); buf = io.BytesIO(); qr.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()

# --- ROTAS ---
@app.route('/')
def index(): return render_template('index.html')

@app.route('/reservar', methods=['POST'])
def reservar():
    novo = Cliente(nome=request.form.get('nome'), telefone=request.form.get('telefone'))
    db.session.add(novo); db.session.commit()
    return redirect(url_for('pagamento', id=novo.id))

@app.route('/pagamento/<int:id>')
def pagamento(id):
    c = Cliente.query.get_or_404(id)
    if c.pago: return redirect(url_for('ingresso', id=c.id))
    try:
        pay_data = {"transaction_amount": 45.0, "description": f"Bafafá - {c.nome}", "payment_method_id": "pix", "payer": {"email": "vendas@bafafa.com"}, "external_reference": str(c.id)}
        res = sdk.payment().create(pay_data)
        qr_pix = res["response"]["point_of_interaction"]["transaction_data"]["qr_code"]
        c.mp_id = str(res["response"]["id"]); db.session.commit()
        return render_template('pagamento.html', c=c, qr_img=gerar_qr_b64(qr_pix), pix_copia_cola=qr_pix, tipo='PIX')
    except: return "Erro no Mercado Pago."

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    if data and data.get("type") == "payment":
        payment_id = data.get("data", {}).get("id")
        payment_info = sdk.payment().get(payment_id)
        if payment_info["response"]["status"] == "approved":
            c = Cliente.query.get(payment_info["response"]["external_reference"])
            if c: c.pago = True; db.session.commit()
    return "", 200

@app.route('/ingresso/<int:id>')
def ingresso(id):
    c = Cliente.query.get_or_404(id)
    if not c.pago: return "Aguardando pagamento..."
    qr_checkin = gerar_qr_b64(f"https://evento-samba.onrender.com/validar-entrada/{c.id}")
    return render_template('obrigado.html', c=c, qr_checkin=qr_checkin)

@app.route('/validar-entrada/<int:id>')
def validar_entrada(id):
    c = Cliente.query.get_or_404(id); c.na_casa = True; db.session.commit()
    return f"<h1>Acesso Liberado: {c.nome}</h1><a href='/portaria'>Voltar</a>"

# --- NOVO FLUXO DO BAR ---
@app.route('/bar-digital/<int:id>', methods=['GET', 'POST'])
def bar_digital(id):
    c = Cliente.query.get_or_404(id)
    if not c.na_casa: return "Check-in pendente na portaria."
    
    if request.method == 'POST':
        prod_id = request.form.get('produto_id')
        db.session.add(Pedido(cliente_id=c.id, produto_id=prod_id, status='No Carrinho'))
        db.session.commit()
        return redirect(url_for('bar_digital', id=c.id))

    produtos = Produto.query.filter(Produto.estoque > 0).all()
    carrinho = Pedido.query.filter_by(cliente_id=c.id, status='No Carrinho').all()
    pedidos_pagos = Pedido.query.filter_by(cliente_id=c.id, status='Pagamento Pendente').all()
    
    qr_pedido = gerar_qr_b64(f"https://evento-samba.onrender.com/confirmar-pedido/{c.id}") if pedidos_pagos else None
    
    return render_template('bar_digital.html', produtos=produtos, c=c, carrinho=carrinho, pedidos=pedidos_pagos, qr_pedido=qr_pedido)

@app.route('/finalizar-carrinho/<int:id>', methods=['POST'])
def finalizar_carrinho(id):
    metodo = request.form.get('metodo_pagamento')
    itens = Pedido.query.filter_by(cliente_id=id, status='No Carrinho').all()
    for item in itens:
        item.status = 'Pagamento Pendente'
        item.metodo_pagamento = metodo
    db.session.commit()
    return redirect(url_for('bar_digital', id=id))

@app.route('/confirmar-pedido/<int:cliente_id>')
def confirmar_pedido(cliente_id):
    pedidos = Pedido.query.filter_by(cliente_id=cliente_id, status='Pagamento Pendente').all()
    func_staff = Equipe.query.filter_by(usuario=session.get('usuario_nome')).first()
    for p in pedidos:
        p.status = 'Entregue'
        prod = Produto.query.get(p.produto_id)
        if prod.estoque > 0: prod.estoque -= 1
        if func_staff: func_staff.caixinha_total += (prod.preco_venda * 0.10)
    db.session.commit()
    return "<h1>PEDIDO ENTREGUE!</h1><a href='/bar-staff'>Voltar</a>"

# --- ADMIN E STAFF ---
@app.route('/admin_total', methods=['GET', 'POST'])
def admin_total():
    if session.get('cargo') != 'admin': return redirect(url_for('login_staff'))
    if request.method == 'POST':
        tipo = request.form.get('form_tipo')
        if tipo == 'equipe':
            db.session.add(Equipe(nome=request.form.get('n'), usuario=request.form.get('u'), senha=request.form.get('s'), cargo=request.form.get('c')))
        elif tipo == 'custo':
            db.session.add(CustoOperacional(descricao=request.form.get('d'), valor=float(request.form.get('v'))))
        db.session.commit()
    
    entradas = db.session.query(func.sum(Cliente.valor_total)).filter_by(pago=True).scalar() or 0
    custos = db.session.query(func.sum(CustoOperacional.valor)).scalar() or 0
    return render_template('admin_total.html', total_entradas=entradas, total_custos=custos, equipe=Equipe.query.all(), produtos=Produto.query.all(), clientes_pendentes=Cliente.query.filter_by(pago=False).all())

@app.route('/login-staff', methods=['GET', 'POST'])
def login_staff():
    if request.method == 'POST':
        u = Equipe.query.filter_by(usuario=request.form.get('username'), senha=request.form.get('senha')).first()
        if u:
            session.update({'cargo': u.cargo, 'usuario_nome': u.usuario})
            return redirect(url_for('admin_total' if u.cargo == 'admin' else 'portaria' if u.cargo == 'portaria' else 'bar_staff'))
    return render_template('login_staff.html')

@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('login_staff'))

@app.route('/reset-bruto-bafafa')
def reset():
    db.drop_all(); db.create_all()
    itens = [
        ("Antarctica Lata", "antarctica.jpg"), ("Brahma Lata", "brahma.jpg"), ("Heineken 350ml", "heineken.jpg")
    ]
    for n, img in itens: db.session.add(Produto(nome=n, imagem_url=img, preco_venda=0, preco_custo=0, estoque=0))
    db.session.add(Equipe(nome='Wagner Master', usuario='wagner', senha='123', cargo='admin'))
    db.session.commit()
    return "✅ RESET OK!"

if __name__ == '__main__':
    with app.app_context(): db.create_all()
    app.run(host='0.0.0.0', port=10000)