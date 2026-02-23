import os, re, mercadopago
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from functools import wraps
from datetime import datetime

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.secret_key = "segredo_bafafa_2026_seguranca_total" # Chave para as sessões de login

# --- BANCO DE DADOS ---
uri = "postgresql://db_fazcomfe_user:bo24NlcJANvGehkj97PytDoNyoiT696V@dpg-d6b4mq4hncsc7386sfag-a/db_fazcomfe?sslmode=require"
app.config['SQLALCHEMY_DATABASE_URI'] = uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- MERCADO PAGO ---
sdk = mercadopago.SDK("APP_USR-3244228687878580-021915-5528b1d97c9055fab65127d73dc1427d-24221819")

# --- MODELOS ---
class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    senha = db.Column(db.String(50), nullable=False)
    cargo = db.Column(db.String(30)) # admin, promoter, portaria, bar, cozinha, etc.

class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100))
    telefone = db.Column(db.String(20), unique=True)
    pago = db.Column(db.Boolean, default=False)
    utilizado = db.Column(db.Boolean, default=False)
    quem_liberou = db.Column(db.String(50))
    data_entrada = db.Column(db.DateTime)
    payment_id = db.Column(db.String(100))

class Produto(db.Model):
    __tablename__ = 'bar_produtos'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    preco = db.Column(db.Float, nullable=False)
    estoque = db.Column(db.Integer, default=0)
    imagem_url = db.Column(db.String(500))

with app.app_context():
    db.create_all()
    # Cria o Wagner como Admin padrão se não existir
    if not Usuario.query.filter_by(username='wagner').first():
        admin = Usuario(username='wagner', senha='123', cargo='admin')
        db.session.add(admin)
        db.session.commit()

# --- TRAVA DE SEGURANÇA ---
def login_obrigatorio(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            return redirect(url_for('login_staff'))
        return f(*args, **kwargs)
    return decorated_function

# --- LOGIN / LOGOUT ---
@app.route('/login-staff', methods=['GET', 'POST'])
def login_staff():
    if request.method == 'POST':
        user = Usuario.query.filter_by(username=request.form.get('username'), senha=request.form.get('senha')).first()
        if user:
            session['usuario_id'] = user.id
            session['usuario_nome'] = user.username
            session['usuario_cargo'] = user.cargo
            return redirect(url_for('admin_evento'))
        return "Usuário ou Senha Inválidos!"
    return render_template('login_staff.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_staff'))

# --- FLUXO DO CLIENTE (PÚBLICO) ---
@app.route('/')
def index(): return render_template('index.html', preco=45.0)

@app.route('/reservar', methods=['POST'])
def reservar():
    nome = request.form.get('nome', '').upper().strip()
    tel = re.sub(r"\D", "", request.form.get('telefone', ''))
    c = Cliente.query.filter_by(telefone=tel).first()
    if not c:
        c = Cliente(nome=nome, telefone=tel)
        db.session.add(c)
        db.session.commit()
    return redirect(url_for('pagamento', id=c.id))

@app.route('/pagamento/<int:id>')
def pagamento(id):
    c = Cliente.query.get_or_404(id)
    pay_data = {
        "transaction_amount": 45.00,
        "description": f"Ingresso Bafafá - {c.nome}",
        "payment_method_id": "pix",
        "payer": {"email": "wagnerzaparolli15@gmail.com"}
    }
    result = sdk.payment().create(pay_data)
    pix = result["response"]["point_of_interaction"]["transaction_data"]
    c.payment_id = str(result["response"]["id"])
    db.session.commit()
    return render_template('pagamento.html', c=c, pix_codigo=pix["qr_code"], qrcode_base64=pix["qr_code_base64"])

@app.route('/ingresso/<int:id>')
def validar_ingresso(id):
    c = Cliente.query.get_or_404(id)
    # Gera o QR Code com o link de validação
    checkin_url = f"https://evento-samba.onrender.com/valida-portaria/{c.id}"
    return render_template('obrigado.html', c=c, checkin_url=checkin_url)

# --- FLUXO DA EQUIPE (PROTEGIDO) ---
@app.route('/valida-portaria/<int:id>')
@login_obrigatorio
def valida_portaria(id):
    c = Cliente.query.get_or_404(id)
    if c.utilizado:
        return f"<h1>❌ ERRO: JÁ UTILIZADO!</h1><p>Liberado por {c.quem_liberou} às {c.data_entrada.strftime('%H:%M')}</p>"
    
    c.utilizado = True
    c.pago = True
    c.quem_liberou = session['usuario_nome']
    c.data_entrada = datetime.now()
    db.session.commit()
    return render_template('recepcao.html', c=c)

@app.route('/admin/evento', methods=['GET', 'POST'])
@login_obrigatorio
def admin_evento():
    if request.method == 'POST':
        if 'new_user' in request.form:
            u = Usuario(username=request.form.get('username'), senha=request.form.get('senha'), cargo=request.form.get('cargo'))
            db.session.add(u)
        elif 'nome_prod' in request.form:
            p = Produto(nome=request.form.get('nome_prod'), preco=float(request.form.get('preco')), estoque=int(request.form.get('estoque')))
            db.session.add(p)
        db.session.commit()
        return redirect(url_for('admin_evento'))

    clientes = Cliente.query.order_by(Cliente.id.desc()).all()
    produtos = Produto.query.all()
    staff = Usuario.query.all()
    return render_template('admin_bar.html', clientes=clientes, produtos=produtos, staff=staff)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)