import os, re, mercadopago
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from functools import wraps

app = Flask(__name__)
app.secret_key = "BAFAFA_SISTEMA_MASTER_2026"

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

# --- FLUXO DO CLIENTE ---
@app.route('/')
def index(): 
    return render_template('index.html')

@app.route('/reservar', methods=['POST'])
def reservar():
    try:
        nome = request.form.get('nome').upper().strip()
        telefone = re.sub(r"\D", "", request.form.get('telefone', ''))
        c = Cliente(nome=nome, telefone=telefone)
        db.session.add(c)
        db.session.commit()
        return redirect(url_for('pagamento', id=c.id))
    except Exception as e:
        return f"Erro ao reservar: {e}"

@app.route('/pagamento/<int:id>')
def pagamento(id):
    c = Cliente.query.get_or_404(id)
    try:
        pay_data = {"transaction_amount": 45.0, "description": f"Bafafá - {c.nome}", "payment_method_id": "pix", "payer": {"email": "wagnerzaparolli15@gmail.com"}}
        result = sdk.payment().create(pay_data)
        pix = result["response"]["point_of_interaction"]["transaction_data"]
        c.payment_id = str(result["response"]["id"])
        db.session.commit()
        return render_template('pagamento.html', c=c, pix_codigo=pix["qr_code"], qrcode_base64=pix["qr_code_base64"])
    except Exception as e:
        return f"Erro no Pix: {e}"

@app.route('/ingresso/<int:id>')
def ingresso(id):
    c = Cliente.query.get_or_404(id)
    if not c.pago:
        try:
            res = sdk.payment().get(c.payment_id)
            if res["response"]["status"] == "approved":
                c.pago = True
                db.session.commit()
            else:
                return render_template('templates-feedback.html', id=id)
        except:
            return render_template('templates-feedback.html', id=id)
    checkin_url = f"https://evento-samba.onrender.com/validar-entrada/{c.id}"
    return render_template('obrigado.html', c=c, checkin_url=checkin_url)

# --- GESTÃO ---
@app.route('/login-staff', methods=['GET', 'POST'])
def login_staff():
    if request.method == 'POST':
        # Ajustado para os nomes 'username' e 'senha' do seu login_staff.html
        f = Equipe.query.filter_by(usuario=request.form.get('username'), senha=request.form.get('senha')).first()
        if f:
            session.update({'staff_id': f.id, 'cargo': f.cargo, 'usuario_nome': f.nome})
            return redirect(url_for('admin_total' if f.cargo == 'admin' else 'portaria'))
    return render_template('login_staff.html')

@app.route('/admin_total', methods=['GET', 'POST'])
def admin_total():
    if request.method == 'POST':
        # Cadastro de equipe
        if 'novo_staff' in request.form:
            e = Equipe(nome=request.form.get('nome'), usuario=request.form.get('user'), senha=request.form.get('pass'), cargo=request.form.get('cargo'))
            db.session.add(e)
        # Gestão de estoque
        if 'id_prod' in request.form:
            p = Produto.query.get(request.form.get('id_prod'))
            p.preco_custo = float(request.form.get('custo'))
            p.preco_venda = float(request.form.get('venda'))
            p.estoque = int(request.form.get('estoque'))
        db.session.commit()
    return render_template('admin_total.html', produtos=Produto.query.all(), equipe=Equipe.query.all(), clientes=Cliente.query.all())

@app.route('/portaria')
def portaria():
    return render_template('portaria.html', clientes=Cliente.query.filter_by(pago=True).all())

@app.route('/validar-entrada/<int:id>')
def validar_entrada(id):
    c = Cliente.query.get_or_404(id)
    c.na_casa = True
    db.session.commit()
    return render_template('recepcao.html', c=c)

@app.route('/bar-digital/<int:id>')
def bar_digital(id):
    c = Cliente.query.get_or_404(id)
    return render_template('bar.html', c=c, produtos=Produto.query.all())

if __name__ == '__main__':
    with app.app_context():
        # db.drop_all() # Use se precisar resetar o banco do zero
        db.create_all()
        if not Equipe.query.filter_by(usuario='wagner').first():
            db.session.add(Equipe(nome='Wagner', usuario='wagner', senha='123', cargo='admin'))
            db.session.commit()
    app.run(host='0.0.0.0', port=10000)