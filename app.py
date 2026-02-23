import os, re, mercadopago
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

app = Flask(__name__, static_folder='static', static_url_path='/static')

# --- BANCO DE DADOS ---
uri = "postgresql://db_fazcomfe_user:bo24NlcJANvGehkj97PytDoNyoiT696V@dpg-d6b4mq4hncsc7386sfag-a/db_fazcomfe?sslmode=require"
app.config['SQLALCHEMY_DATABASE_URI'] = uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- MERCADO PAGO ---
sdk = mercadopago.SDK("APP_USR-3244228687878580-021915-5528b1d97c9055fab65127d73dc1427d-24221819")

# --- MODELOS (NÃO APAGAR NADA) ---
class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100))
    telefone = db.Column(db.String(20), unique=True)
    pago = db.Column(db.Boolean, default=False)
    utilizado = db.Column(db.Boolean, default=False)
    payment_id = db.Column(db.String(100))

class Produto(db.Model):
    __tablename__ = 'bar_produtos'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    preco = db.Column(db.Float, nullable=False)
    preco_custo = db.Column(db.Float, default=0.0)
    estoque = db.Column(db.Integer, default=0)
    imagem_url = db.Column(db.String(500))

with app.app_context():
    db.create_all()

# --- ROTAS DE VENDA ---
@app.route('/')
def index():
    return render_template('index.html', preco=45.0)

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
    if not c.pago and c.payment_id:
        info = sdk.payment().get(c.payment_id)
        if info["response"].get("status") == "approved":
            c.pago = True
            db.session.commit()
        else:
            return render_template('templates-feedback.html', tipo='aguardando')
    checkin_url = f"https://evento-samba.onrender.com/checkin/{c.id}"
    return render_template('obrigado.html', nome=c.nome, id_reserva=c.id, checkin_url=checkin_url)

# --- ADMINISTRAÇÃO CENTRALIZADA (PORTARIA + BAR) ---
@app.route('/admin/evento', methods=['GET', 'POST'])
def admin_evento():
    if request.method == 'POST':
        p = Produto(
            nome=request.form.get('nome'),
            preco=float(request.form.get('preco_venda')),
            preco_custo=float(request.form.get('preco_custo')),
            estoque=int(request.form.get('estoque')),
            imagem_url=request.form.get('imagem_url')
        )
        db.session.add(p)
        db.session.commit()
        return redirect(url_for('admin_evento'))
    
    produtos = Produto.query.all()
    clientes = Cliente.query.order_by(Cliente.id.desc()).all()
    return render_template('admin_bar.html', produtos=produtos, clientes=clientes)

@app.route('/checkin/<int:id>')
def checkin(id):
    c = Cliente.query.get_or_404(id)
    c.pago = True
    c.utilizado = True
    db.session.commit()
    return redirect(url_for('admin_evento'))

@app.route('/admin/reset-total')
def reset_total():
    db.session.execute(text("TRUNCATE TABLE bar_produtos, cliente RESTART IDENTITY CASCADE;"))
    db.session.commit()
    return "<h1>Sistema Limpo!</h1><a href='/admin/evento'>Voltar</a>"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)