import os, re, mercadopago
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from datetime import datetime

app = Flask(__name__)
app.secret_key = "BAFAFA_SISTEMA_TOTAL_2026"

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
    cargo = db.Column(db.String(30)) # admin, portaria, bar, seguranca, limpeza, musico, carregador

class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100))
    telefone = db.Column(db.String(20))
    pago = db.Column(db.Boolean, default=False)
    na_casa = db.Column(db.Boolean, default=False) # Liberado pelo QR Code na portaria
    payment_id = db.Column(db.String(100))

class Produto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100))
    preco_custo = db.Column(db.Float, default=0.0)
    preco_venda = db.Column(db.Float, default=0.0)
    estoque = db.Column(db.Integer, default=0)

# --- DECORATOR DE SEGURANÇA ---
def login_staff_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'staff_id' not in session: return redirect(url_for('login_staff'))
        return f(*args, **kwargs)
    return decorated

# --- 🟢 FLUXO DO CLIENTE (INGRESSO -> PIX -> QR -> BAR) ---
@app.route('/')
def index(): return render_template('index.html')

@app.route('/reservar', methods=['POST'])
def reservar():
    c = Cliente(nome=request.form.get('nome').upper().strip(), telefone=request.form.get('telefone'))
    db.session.add(c); db.session.commit()
    return redirect(url_for('pagamento', id=c.id))

@app.route('/pagamento/<int:id>')
def pagamento(id):
    c = Cliente.query.get_or_404(id)
    # Lógica de geração de PIX Mercado Pago aqui (omitida para brevidade)
    return render_template('pagamento.html', c=c)

@app.route('/meu-ingresso/<int:id>')
def ingresso_qr(id):
    c = Cliente.query.get_or_404(id)
    if not c.pago: return redirect(url_for('pagamento', id=id))
    # Link que o segurança vai escanear
    checkin_url = f"https://evento-samba.onrender.com/validar-entrada/{c.id}"
    return render_template('obrigado.html', c=c, checkin_url=checkin_url)

@app.route('/recepcao/<int:id>')
def recepcao(id):
    c = Cliente.query.get_or_404(id)
    if not c.na_casa: return "<h1>ACESSO NEGADO</h1><p>Vá até a portaria primeiro.</p>"
    produtos = Produto.query.filter(Produto.estoque > 0).all()
    return render_template('recepcao.html', c=c, produtos=produtos)

# --- 🔴 PAINEL ADMIN MASTER (ADMINISTRA TUDO) ---
@app.route('/admin_total', methods=['GET', 'POST'])
@login_staff_required
def admin_total():
    if session['cargo'] != 'admin': return "Acesso Negado"
    
    if request.method == 'POST':
        if 'novo_staff' in request.form:
            f = Equipe(nome=request.form.get('nome'), usuario=request.form.get('user'), 
                       senha=request.form.get('pass'), cargo=request.form.get('cargo'))
            db.session.add(f)
        elif 'id_prod' in request.form:
            p = Produto.query.get(request.form.get('id_prod'))
            p.preco_custo = float(request.form.get('custo'))
            p.preco_venda = float(request.form.get('venda'))
            p.estoque = int(request.form.get('estoque'))
        db.session.commit()

    return render_template('admin_total.html', 
                           clientes=Cliente.query.all(), 
                           equipe=Equipe.query.all(), 
                           produtos=Produto.query.all())

@app.route('/validar-entrada/<int:id>')
@login_staff_required
def validar_entrada(id):
    c = Cliente.query.get_or_404(id)
    c.na_casa = True # Libera o Bar Digital automaticamente
    db.session.commit()
    return redirect(url_for('portaria'))

@app.route('/login-staff', methods=['GET', 'POST'])
def login_staff():
    if request.method == 'POST':
        f = Equipe.query.filter_by(usuario=request.form.get('u'), senha=request.form.get('s')).first()
        if f:
            session.update({'staff_id': f.id, 'cargo': f.cargo, 'nome': f.nome})
            return redirect(url_for('admin_total' if f.cargo == 'admin' else 'portaria'))
    return render_template('login_staff.html')

if __name__ == '__main__':
    with app.app_context(): db.create_all()
    app.run(host='0.0.0.0', port=10000)