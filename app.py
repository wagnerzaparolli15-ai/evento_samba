import os, re, mercadopago
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from datetime import datetime

app = Flask(__name__)
app.secret_key = "BAFAFA_SISTEMA_DEFINITIVO_2026"

# --- BANCO DE DADOS ---
uri = "postgresql://db_fazcomfe_user:bo24NlcJANvGehkj97PytDoNyoiT696V@dpg-d6b4mq4hncsc7386sfag-a/db_fazcomfe?sslmode=require"
app.config['SQLALCHEMY_DATABASE_URI'] = uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- MERCADO PAGO ---
sdk = mercadopago.SDK("APP_USR-3244228687878580-021915-5528b1d97c9055fab65127d73dc1427d-24221819")

# --- MODELOS ---
class Equipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100))
    usuario = db.Column(db.String(50), unique=True)
    senha = db.Column(db.String(50))
    cargo = db.Column(db.String(30)) 

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

# --- SEGURANÇA ---
def login_staff_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'staff_id' not in session: return redirect(url_for('login_staff'))
        return f(*args, **kwargs)
    return decorated

# --- FLUXO DO CLIENTE (DO INÍCIO AO FIM) ---

@app.route('/')
def index(): 
    return render_template('index.html')

@app.route('/reservar', methods=['POST'])
def reservar():
    nome = request.form.get('nome').upper().strip()
    telefone = re.sub(r"\D", "", request.form.get('telefone', ''))
    c = Cliente(nome=nome, telefone=telefone)
    db.session.add(c)
    db.session.commit()
    return redirect(url_for('pagamento', id=c.id))

@app.route('/pagamento/<int:id>')
def pagamento(id):
    c = Cliente.query.get_or_404(id)
    # Gerando PIX Mercado Pago
    pay_data = {
        "transaction_amount": 45.0,
        "description": f"Bafafá - {c.nome}",
        "payment_method_id": "pix",
        "payer": {"email": "wagnerzaparolli15@gmail.com"}
    }
    result = sdk.payment().create(pay_data)
    pix = result["response"]["point_of_interaction"]["transaction_data"]
    c.payment_id = str(result["response"]["id"])
    db.session.commit()
    return render_template('pagamento.html', c=c, pix_codigo=pix["qr_code"], qrcode_base64=pix["qr_code_base64"])

@app.route('/ingresso/<int:id>')
def ingresso(id):
    c = Cliente.query.get_or_404(id)
    # Se ainda não pagou, manda para a página de espera (feedback)
    if not c.pago:
        # Verifica no Mercado Pago
        status = sdk.payment().get(c.payment_id)["response"]["status"]
        if status == "approved":
            c.pago = True
            db.session.commit()
        else:
            return render_template('templates-feedback.html', id=id)
            
    checkin_url = f"https://evento-samba.onrender.com/validar-entrada/{c.id}"
    return render_template('obrigado.html', c=c, checkin_url=checkin_url)

# --- FLUXO DE GESTÃO ---

@app.route('/login-staff', methods=['GET', 'POST'])
def login_staff():
    if request.method == 'POST':
        f = Equipe.query.filter_by(usuario=request.form.get('u'), senha=request.form.get('s')).first()
        if f:
            session.update({'staff_id': f.id, 'cargo': f.cargo, 'nome': f.nome})
            return redirect(url_for('admin_total' if f.cargo == 'admin' else 'portaria'))
    return render_template('login_staff.html')

@app.route('/admin_total', methods=['GET', 'POST'])
@login_staff_required
def admin_total():
    if session['cargo'] != 'admin': return "Acesso negado"
    if request.method == 'POST':
        if 'id_prod' in request.form:
            p = Produto.query.get(request.form.get('id_prod'))
            p.preco_custo = float(request.form.get('custo'))
            p.preco_venda = float(request.form.get('venda'))
            p.estoque = int(request.form.get('estoque'))
        db.session.commit()
    
    prods = Produto.query.all()
    c_tot = sum([p.preco_custo * p.estoque for p in prods])
    lucro = sum([(p.preco_venda - p.preco_custo) * p.estoque for p in prods])
    return render_template('admin_total.html', produtos=prods, custo_total=c_tot, lucro=lucro, clientes=Cliente.query.all())

@app.route('/portaria')
@login_staff_required
def portaria():
    return render_template('portaria.html', clientes=Cliente.query.filter_by(pago=True).all())

@app.route('/validar-entrada/<int:id>')
@login_staff_required
def validar_entrada(id):
    c = Cliente.query.get_or_404(id)
    c.na_casa = True
    db.session.commit()
    return redirect(url_for('portaria'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Cria admin padrão se não existir
        if not Equipe.query.filter_by(usuario='wagner').first():
            db.session.add(Equipe(nome='Wagner', usuario='wagner', senha='123', cargo='admin'))
            db.session.commit()
    app.run(host='0.0.0.0', port=10000)