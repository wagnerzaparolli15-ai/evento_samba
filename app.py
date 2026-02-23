import os, re, mercadopago
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from functools import wraps

app = Flask(__name__)
app.secret_key = "SISTEMA_BAFAFA_2026_TOTAL"

# --- 1. CONFIGURAÇÃO DO BANCO DE DADOS ---
uri = "postgresql://db_fazcomfe_user:bo24NlcJANvGehkj97PytDoNyoiT696V@dpg-d6b4mq4hncsc7386sfag-a/db_fazcomfe?sslmode=require"
app.config['SQLALCHEMY_DATABASE_URI'] = uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- 2. CONFIGURAÇÃO MERCADO PAGO ---
sdk = mercadopago.SDK("APP_USR-3244228687878580-021915-5528b1d97c9055fab65127d73dc1427d-24221819")

# --- 3. MODELOS DE DADOS ---
class Equipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100))
    usuario = db.Column(db.String(50), unique=True)
    senha = db.Column(db.String(50))
    cargo = db.Column(db.String(30))
    cachet = db.Column(db.Float, default=0.0)

class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100))
    telefone = db.Column(db.String(20))
    pago = db.Column(db.Boolean, default=False)
    na_casa = db.Column(db.Boolean, default=False)
    payment_id = db.Column(db.String(100))

class Produto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100))
    preco_custo = db.Column(db.Float, default=0.0)
    preco_venda = db.Column(db.Float, default=0.0)
    estoque = db.Column(db.Integer, default=0)
    vendidos = db.Column(db.Integer, default=0)

# --- 4. FLUXO DO CLIENTE ---
@app.route('/')
def index(): 
    return render_template('index.html')

@app.route('/reservar', methods=['POST'])
def reservar():
    nome = request.form.get('nome').upper().strip()
    tel = request.form.get('telefone')
    c = Cliente(nome=nome, telefone=tel)
    db.session.add(c)
    db.session.commit()
    return redirect(url_for('pagamento', id=c.id))

@app.route('/pagamento/<int:id>')
def pagamento(id):
    c = Cliente.query.get_or_404(id)
    payment_data = {
        "transaction_amount": 45.0,
        "description": "Ingresso Bafafá",
        "payment_method_id": "pix",
        "payer": {"email": "vendas@bafafa.com"}
    }
    payment_response = sdk.payment().create(payment_data)
    payment = payment_response["response"]
    c.payment_id = str(payment["id"])
    db.session.commit()
    
    return render_template('pagamento.html', 
                           c=c, 
                           pix_codigo=payment["point_of_interaction"]["transaction_data"]["qr_code"], 
                           qrcode_base64=payment["point_of_interaction"]["transaction_data"]["qr_code_base64"])

@app.route('/ingresso/<int:id>')
def ingresso(id):
    c = Cliente.query.get_or_404(id)
    if not c.pago:
        res = sdk.payment().get(c.payment_id)
        if res.get("response", {}).get("status") == "approved":
            c.pago = True
            db.session.commit()
        else:
            return render_template('templates-feedback.html', id=id)
    
    checkin_url = url_for('validar_entrada', id=c.id, _external=True)
    return render_template('obrigado.html', c=c, checkin_url=checkin_url)

# --- 5. GESTÃO E AMBIENTES ---
@app.route('/login-staff', methods=['GET', 'POST'])
def login_staff():
    if request.method == 'POST':
        u = request.form.get('username')
        s = request.form.get('senha')
        f = Equipe.query.filter_by(usuario=u, senha=s).first()
        if f:
            session.update({'staff_id': f.id, 'cargo': f.cargo, 'usuario_nome': f.nome})
            return redirect(url_for('admin_total' if f.cargo == 'admin' else 'portaria'))
    return render_template('login_staff.html')

@app.route('/portaria')
def portaria():
    if 'staff_id' not in session: return redirect(url_for('login_staff'))
    # Mostra apenas quem pagou e ainda não entrou
    clientes = Cliente.query.filter_by(pago=True, na_casa=False).all()
    return render_template('portaria.html', clientes=clientes)

@app.route('/validar-entrada/<int:id>')
def validar_entrada(id):
    c = Cliente.query.get_or_404(id)
    c.na_casa = True
    db.session.commit()
    return render_template('recepcao.html', c=c)

@app.route('/bar-digital/<int:id>')
def bar_digital(id):
    c = Cliente.query.get_or_404(id)
    if not c.na_casa: return "Acesso negado. Por favor, valide sua entrada na portaria.", 403
    produtos = Produto.query.filter(Produto.estoque > 0).all()
    return render_template('bar.html', c=c, produtos=produtos)

# Rota para o Barman ou Sistema dar baixa na venda
@app.route('/comprar_item', methods=['POST'])
def comprar_item():
    data = request.json
    for item in data.get('itens', []):
        p = Produto.query.get(item['id'])
        if p and p.estoque > 0:
            p.estoque -= 1
            p.vendidos += 1
    db.session.commit()
    return jsonify({"status": "success"})

@app.route('/admin_total', methods=['GET', 'POST'])
def admin_total():
    if session.get('cargo') != 'admin': return redirect(url_for('login_staff'))
    
    if request.method == 'POST':
        if 'novo_staff' in request.form:
            e = Equipe(nome=request.form.get('nome'), usuario=request.form.get('user'), 
                       senha=request.form.get('pass'), cargo=request.form.get('cargo'),
                       cachet=float(request.form.get('cachet') or 0))
            db.session.add(e)
        if 'id_prod' in request.form:
            p = Produto.query.get(request.form.get('id_prod'))
            p.preco_custo = float(request.form.get('custo'))
            p.preco_venda = float(request.form.get('venda'))
            p.estoque = int(request.form.get('estoque'))
        db.session.commit()

    # Contabilidade Consolidada
    venda_ingressos = db.session.query(db.func.count(Cliente.id)).filter(Cliente.pago == True).scalar() * 45.0
    venda_bar = sum([p.preco_venda * p.vendidos for p in Produto.query.all()])
    custo_equipe = db.session.query(db.func.sum(Equipe.cachet)).scalar() or 0
    custo_produtos = sum([p.preco_custo * p.vendidos for p in Produto.query.all()])
    
    fin = {
        "receita": venda_ingressos + venda_bar, 
        "despesas": custo_equipe + custo_produtos, 
        "lucro": (venda_ingressos + venda_bar) - (custo_equipe + custo_produtos)
    }
    return render_template('admin_total.html', equipe=Equipe.query.all(), produtos=Produto.query.all(), clientes=Cliente.query.all(), fin=fin)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.drop_all()  # <--- ESSA LINHA VAI LIMPAR O ERRO
        db.create_all()
        if not Equipe.query.filter_by(usuario='wagner').first():
            db.session.add(Equipe(nome='Wagner', usuario='wagner', senha='123', cargo='admin', cachet=0))
            db.session.commit()
    app.run(host='0.0.0.0', port=10000)