import os, mercadopago, qrcode, io, base64, datetime
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func

app = Flask(__name__)

# --- CONFIGURAÇÃO MASTER ---
db_url = os.getenv("DATABASE_URL")
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url or "sqlite:///bafafa_master_2026.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.getenv("SECRET_KEY", "BAFAFA_TOTAL_CONTROL_2026")

db = SQLAlchemy(app)
sdk = mercadopago.SDK(os.getenv("MP_ACCESS_TOKEN"))

# --- MODELOS DE DADOS (ECOSSISTEMA) ---
class Equipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100)); usuario = db.Column(db.String(50), unique=True)
    senha = db.Column(db.String(50)); cargo = db.Column(db.String(30)); cachet = db.Column(db.Float, default=0.0)

class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True); nome = db.Column(db.String(100)); telefone = db.Column(db.String(20))
    pago = db.Column(db.Boolean, default=False); na_casa = db.Column(db.Boolean, default=False)
    metodo = db.Column(db.String(20), default="pix"); payment_id = db.Column(db.String(100))
    valor_total = db.Column(db.Float, default=45.0); quem_liberou = db.Column(db.String(50))

class Produto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100)); imagem = db.Column(db.String(100))
    preco_custo = db.Column(db.Float, default=0.0); preco_venda = db.Column(db.Float, default=0.0)
    estoque = db.Column(db.Integer, default=0)

class CustoEvento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(100)); valor = db.Column(db.Float, default=0.0)

class PedidoBar(db.Model):
    id = db.Column(db.Integer, primary_key=True); cliente_id = db.Column(db.Integer)
    itens = db.Column(db.Text); valor_total = db.Column(db.Float); pago = db.Column(db.Boolean, default=False); entregue = db.Column(db.Boolean, default=False)

# --- AUXILIARES (QR CODE) ---
def gerar_qr_base64(conteudo):
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(conteudo); qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO(); img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()

# --- ADMINISTRAÇÃO TOTAL ---
@app.route('/admin_total', methods=['GET', 'POST'])
def admin_total():
    if session.get('cargo') not in ['admin', 'gerente', 'produtor']: return redirect(url_for('login_staff'))
    if request.method == 'POST':
        tipo = request.form.get('form_tipo')
        if tipo == 'produto':
            db.session.add(Produto(nome=request.form.get('n'), preco_custo=float(request.form.get('pc')), preco_venda=float(request.form.get('pv')), estoque=int(request.form.get('e')), imagem=request.form.get('img')))
        elif tipo == 'equipe':
            db.session.add(Equipe(nome=request.form.get('n'), usuario=request.form.get('u'), senha=request.form.get('s'), cargo=request.form.get('c'), cachet=float(request.form.get('v'))))
        elif tipo == 'custo':
            db.session.add(CustoEvento(descricao=request.form.get('d'), valor=float(request.form.get('v'))))
        db.session.commit()

    vendas = db.session.query(func.sum(Cliente.valor_total)).filter(Cliente.pago==True).scalar() or 0
    custos = (db.session.query(func.sum(CustoEvento.valor)).scalar() or 0) + (db.session.query(func.sum(Equipe.cachet)).scalar() or 0)
    
    fin = {"equipe": Equipe.query.all(), "produtos": Produto.query.all(), "pendentes": Cliente.query.filter_by(pago=False).all(), "vendas": vendas, "custos": custos}
    return render_template('admin_total.html', fin=fin)

# --- BAR DIGITAL (PAGINA DO CLIENTE) ---
@app.route('/bar-digital/<int:id>')
def bar_digital(id):
    c = Cliente.query.get_or_404(id)
    prods = Produto.query.filter(Produto.estoque > 0).all()
    return render_template('bar.html', c=c, produtos=prods)

# --- CONFIRMAÇÃO MANUAL (VIP/DINHEIRO) ---
@app.route('/confirmar-direto/<int:id>')
def confirmar_direto(id):
    c = Cliente.query.get_or_404(id)
    c.pago = True; c.metodo = request.args.get('m', 'VIP').upper(); c.quem_liberou = session.get('usuario_nome'); db.session.commit()
    return jsonify({"status": "sucesso"})

# --- FLUXO CLIENTE ---
@app.route('/')
def index(): return render_template('index.html')

@app.route('/reservar', methods=['POST'])
def reservar():
    c = Cliente(nome=request.form.get('nome', '').upper().strip(), telefone=request.form.get('telefone', ''))
    db.session.add(c); db.session.commit()
    return redirect(url_for('pagamento', id=c.id))

@app.route('/pagamento/<int:id>')
def pagamento(id):
    c = Cliente.query.get_or_404(id)
    tipo = request.args.get('tipo', 'pix')
    res = sdk.payment().create({"transaction_amount": 45.0, "description": "Bafafá 2026", "payment_method_id": tipo, "notification_url": url_for('webhook', _external=True), "payer": {"email": "vendas@bafafa.com"}})
    c.payment_id = str(res["response"]["id"]); c.metodo = tipo; db.session.commit()
    qr_c = res["response"]["point_of_interaction"]["transaction_data"]["qr_code"] if tipo == 'pix' else res["response"]["init_point"]
    return render_template('pagamento.html', c=c, qr_img=gerar_qr_base64(qr_c), tipo=tipo)

@app.route('/ingresso/<int:id>')
def ingresso(id):
    c = Cliente.query.get_or_404(id)
    if not c.pago: return render_template('templates-feedback.html', c=c)
    qr_v = gerar_qr_base64(url_for('ingresso', id=c.id, _external=True))
    return render_template('obrigado.html', c=c, qr_code=qr_v)

@app.route('/reset-bruto-bafafa')
def reset():
    db.drop_all(); db.create_all()
    db.session.add(Equipe(nome='Wagner Master', usuario='wagner', senha='123', cargo='admin'))
    db.session.commit()
    return "✅ SISTEMA RESETADO!"

if __name__ == '__main__':
    with app.app_context(): db.create_all()
    app.run(host='0.0.0.0', port=10000)