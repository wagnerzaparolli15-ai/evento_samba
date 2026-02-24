import os, mercadopago, qrcode, io, base64, json, datetime
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func

app = Flask(__name__)

# --- CONFIGURAÇÃO MASTER ---
db_url = os.getenv("DATABASE_URL")
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url or "sqlite:///bafafa_final_2026.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.getenv("SECRET_KEY", "CHAVE_MESTRA_BAFAFA_2026")

db = SQLAlchemy(app)
sdk = mercadopago.SDK(os.getenv("MP_ACCESS_TOKEN"))

# --- MODELOS DE DADOS (INTEGRIDADE TOTAL) ---
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

class CustoOperacional(db.Model):
    id = db.Column(db.Integer, primary_key=True); descricao = db.Column(db.String(100)); valor = db.Column(db.Float)

# --- AUXILIARES (QR CODE) ---
def gerar_qr_base64(conteudo):
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(conteudo); qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO(); img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()

# --- ROTAS DE FLUXO CLIENTE ---
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
        c.payment_id = str(res["response"]["id"]); db.session.commit()
        qr_pix = res["response"]["point_of_interaction"]["transaction_data"]["qr_code"]
        return render_template('pagamento.html', c=c, qr_img=gerar_qr_base64(qr_pix), tipo="pix")
    except: return "Erro ao ligar ao Mercado Pago. Verifique o Token no Render.", 500

@app.route('/ingresso/<int:id>')
def ingresso(id):
    c = Cliente.query.get_or_404(id)
    if not c.pago: return render_template('templates-feedback.html', c=c)
    return render_template('obrigado.html', c=c)

# --- ROTAS DE STAFF E ADMIN MASTER ---
@app.route('/login-staff', methods=['GET', 'POST'])
def login_staff():
    if request.method == 'POST':
        u = Equipe.query.filter_by(usuario=request.form.get('username'), senha=request.form.get('senha')).first()
        if u:
            session.update({'cargo': u.cargo, 'usuario_nome': u.nome})
            if u.cargo in ['admin', 'gerente']: return redirect(url_for('admin_total'))
            if u.cargo == 'portaria': return redirect(url_for('portaria'))
    return render_template('login_staff.html')

@app.route('/admin_total', methods=['GET', 'POST'])
def admin_total():
    if session.get('cargo') not in ['admin', 'gerente']: return redirect(url_for('login_staff'))
    
    if request.method == 'POST':
        tipo = request.form.get('form_tipo')
        if tipo == 'produto':
            db.session.add(Produto(nome=request.form.get('n'), preco_custo=float(request.form.get('pc')), preco_venda=float(request.form.get('pv')), estoque=int(request.form.get('e')), imagem=request.form.get('img')))
        elif tipo == 'custo':
            db.session.add(CustoOperacional(descricao=request.form.get('d'), valor=float(request.form.get('v'))))
        db.session.commit()

    entradas = db.session.query(func.sum(Cliente.valor_total)).filter(Cliente.pago==True).scalar() or 0
    custos_op = db.session.query(func.sum(CustoOperacional.valor)).scalar() or 0
    custos_staff = db.session.query(func.sum(Equipe.cachet)).scalar() or 0
    
    return render_template('admin_total.html', 
                           total_entradas=entradas, 
                           total_custos=(custos_op + custos_staff),
                           clientes_pendentes=Cliente.query.filter_by(pago=False).all(),
                           produtos=Produto.query.all())

@app.route('/portaria')
def portaria():
    if session.get('cargo') not in ['admin', 'portaria']: return redirect(url_for('login_staff'))
    clientes = Cliente.query.filter_by(pago=True, na_casa=False).all()
    return render_template('portaria.html', clientes=clientes)

@app.route('/validar-entrada/<int:id>')
def validar_entrada(id):
    c = Cliente.query.get_or_404(id)
    c.na_casa = True; db.session.commit()
    return render_template('recepcao.html', c=c)

@app.route('/bar-digital/<int:id>')
def bar_digital(id):
    c = Cliente.query.get_or_404(id)
    produtos = Produto.query.filter(Produto.estoque > 0).all()
    return render_template('bar.html', c=c, produtos=produtos)

@app.route('/reset-bruto-bafafa')
def reset():
    db.drop_all(); db.create_all()
    db.session.add(Equipe(nome='Wagner Master', usuario='wagner', senha='123', cargo='admin'))
    db.session.commit()
    return "✅ SISTEMA RESETADO! Login: wagner / 123"

@app.route('/webhook', methods=['POST'])
def webhook(): return "OK", 200

if __name__ == '__main__':
    with app.app_context(): db.create_all()
    app.run(host='0.0.0.0', port=10000)