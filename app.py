import os, re, mercadopago
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

app = Flask(__name__)

# --- BANCO DE DADOS (PostgreSQL Render) ---
uri = "postgresql://db_fazcomfe_user:bo24NlcJANvGehkj97PytDoNyoiT696V@dpg-d6b4mq4hncsc7386sfag-a/db_fazcomfe?sslmode=require"
app.config['SQLALCHEMY_DATABASE_URI'] = uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- MERCADO PAGO ---
sdk = mercadopago.SDK("APP_USR-3244228687878580-021915-5528b1d97c9055fab65127d73dc1427d-24221819")

# --- MODELOS DE DADOS ---
class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100))
    telefone = db.Column(db.String(20), unique=True)
    pago = db.Column(db.Boolean, default=False)
    utilizado = db.Column(db.Boolean, default=False)

class Produto(db.Model):
    __tablename__ = 'bar_produtos'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    preco = db.Column(db.Float, nullable=False)
    preco_custo = db.Column(db.Float, default=0.0)
    estoque = db.Column(db.Integer, default=0)
    imagem_url = db.Column(db.String(500)) # Link da foto/logo
    ativo = db.Column(db.Boolean, default=True)

# --- ROTAS DO CLIENTE ---

@app.route('/')
def index():
    return render_template('index.html', preco=45.0)

@app.route('/reservar', methods=['POST'])
def reservar():
    try:
        nome = request.form.get('nome', '').upper().strip()
        tel = re.sub(r"\D", "", request.form.get('telefone', ''))
        c = Cliente.query.filter_by(telefone=tel).first()
        if not c:
            c = Cliente(nome=nome, telefone=tel)
            db.session.add(c)
            db.session.commit()
        return redirect(url_for('pagamento', id=c.id))
    except Exception as e:
        return f"Erro ao reservar: {str(e)}"

@app.route('/pagamento/<int:id>')
def pagamento(id):
    c = Cliente.query.get_or_404(id)
    # Gera o Pix de R$ 45,00
    pay_data = {
        "transaction_amount": 45.00,
        "description": f"Ingresso Bafafá - {c.nome}",
        "payment_method_id": "pix",
        "payer": {"email": "wagnerzaparolli15@gmail.com"}
    }
    result = sdk.payment().create(pay_data)
    pix = result["response"]["point_of_interaction"]["transaction_data"]
    return render_template('pagamento.html', c=c, pix_codigo=pix["qr_code"], qrcode_base64=pix["qr_code_base64"])

@app.route('/ingresso/<int:id>')
def validar_ingresso(id):
    c = Cliente.query.get_or_404(id)
    if c.utilizado: return redirect(url_for('bar', id=c.id))
    if c.pago: return render_template('recepcao.html', c=c)
    return render_template('templates-feedback.html', tipo='aguardando', id=c.id)

@app.route('/bar/<int:id>')
def bar(id):
    c = Cliente.query.get_or_404(id)
    produtos = Produto.query.filter_by(ativo=True).all()
    return render_template('bar.html', c=c, produtos=produtos)

# --- ROTAS DE GESTÃO (ADMIN) ---

@app.route('/admin/bar/produtos', methods=['GET', 'POST'])
def admin_bar_produtos():
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
        return redirect(url_for('admin_bar_produtos'))
    
    try:
        produtos = Produto.query.all()
        clientes = Cliente.query.order_by(Cliente.id.desc()).all()
    except:
        produtos, clientes = [], []
    return render_template('admin_bar.html', produtos=produtos, clientes=clientes)

@app.route('/checkin/<int:id>')
def checkin(id):
    c = Cliente.query.get_or_404(id)
    c.utilizado = True
    c.pago = True # Libera o acesso ao bar
    db.session.commit()
    return redirect(url_for('admin_bar_produtos'))

@app.route('/admin/reset-total')
def reset_total():
    try:
        # COMANDO CASCADE: Remove todas as travas e tabelas presas
        db.session.execute(text("DROP TABLE IF EXISTS bar_produtos CASCADE;"))
        db.session.execute(text("DROP TABLE IF EXISTS cliente CASCADE;"))
        db.session.commit()
        db.create_all()
        return "<h1>Sucesso! O Bafafá está limpo e as tabelas foram recriadas.</h1>"
    except Exception as e:
        return f"<h1>Erro ao resetar: {str(e)}</h1>"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)