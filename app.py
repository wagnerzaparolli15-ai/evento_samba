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

# --- MODELOS DE DADOS ---
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
    id = db.Column(db.Integer, primary_key=True); nome = db.Column(db.String(100))
    imagem = db.Column(db.String(100)); preco_custo = db.Column(db.Float, default=0.0)
    preco_venda = db.Column(db.Float, default=0.0); estoque = db.Column(db.Integer, default=0)

class PedidoBar(db.Model):
    id = db.Column(db.Integer, primary_key=True); cliente_id = db.Column(db.Integer)
    itens = db.Column(db.Text); valor_total = db.Column(db.Float); entregue = db.Column(db.Boolean, default=False)

# --- AUXILIARES (QR CODE) ---
def gerar_qr_base64(conteudo):
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(conteudo); qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO(); img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()

# --- ROTAS DE FLUXO ---
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
    try:
        res = sdk.payment().create({
            "transaction_amount": 45.0, "description": "Bafafá 2026", "payment_method_id": "pix",
            "notification_url": url_for('webhook', _external=True), "payer": {"email": "vendas@bafafa.com"}
        })
        if res["status"] == 201:
            c.payment_id = str(res["response"]["id"]); db.session.commit()
            qr_img = gerar_qr_base64(res["response"]["point_of_interaction"]["transaction_data"]["qr_code"])
            return render_template('pagamento.html', c=c, qr_img=qr_img, tipo="pix")
        return "Erro ao gerar PIX. Verifique seu Token no Render.", 500
    except: return "Sistema de pagamentos offline.", 500

@app.route('/admin_total', methods=['GET', 'POST'])
def admin_total():
    if session.get('cargo') not in ['admin', 'gerente']: return redirect(url_for('login_staff'))
    # Lógica de POST para cadastrar produtos e staff...
    fin = {"lucro": 0, "pendentes": Cliente.query.filter_by(pago=False).all()}
    return render_template('admin_total.html', fin=fin, equipe=Equipe.query.all())

@app.route('/confirmar-direto/<int:id>')
@app.route('/confirmar-manual-admin/<int:id>')
def confirmar_manual(id):
    c = Cliente.query.get_or_404(id)
    c.pago = True; c.metodo = request.args.get('m', 'VIP').upper(); db.session.commit()
    return jsonify({"status": "sucesso"})

@app.route('/reset-bruto-bafafa')
def reset():
    db.drop_all(); db.create_all()
    db.session.add(Equipe(nome='Wagner', usuario='wagner', senha='123', cargo='admin'))
    db.session.commit()
    return "✅ SISTEMA RESETADO!"

@app.route('/webhook', methods=['POST'])
def webhook(): return "OK", 200

if __name__ == '__main__':
    with app.app_context(): db.create_all()
    app.run(host='0.0.0.0', port=10000)