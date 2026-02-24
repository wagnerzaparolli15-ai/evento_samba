import os, mercadopago, datetime, qrcode, io, base64
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func

app = Flask(__name__)

# --- CONFIGURAÇÃO DE AMBIENTE ---
db_url = os.getenv("DATABASE_URL")
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url or "sqlite:///bafafa_master_2026.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.getenv("SECRET_KEY", "BAFAFA_TOTAL_CONTROL_2026")

db = SQLAlchemy(app)
sdk = mercadopago.SDK(os.getenv("MP_ACCESS_TOKEN"))

# --- MODELOS DE DADOS (ESTRUTURA UNIFICADA) ---
class Equipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100))
    usuario = db.Column(db.String(50), unique=True)
    senha = db.Column(db.String(50))
    cargo = db.Column(db.String(30)) # admin, gerente, produtor, portaria, bar, seguranca, limpeza, musico
    cachet = db.Column(db.Float, default=0.0)

class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100))
    telefone = db.Column(db.String(20))
    pago = db.Column(db.Boolean, default=False)
    na_casa = db.Column(db.Boolean, default=False)
    metodo = db.Column(db.String(20), default="pix")
    payment_id = db.Column(db.String(100))
    valor_total = db.Column(db.Float, default=45.0)
    quem_liberou = db.Column(db.String(50))
    hora_entrada = db.Column(db.String(20))

class CustoEvento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(100))
    valor = db.Column(db.Float, default=0.0)

class Produto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100))
    preco_custo = db.Column(db.Float, default=0.0)
    preco_venda = db.Column(db.Float, default=0.0)
    estoque = db.Column(db.Integer, default=0)

class PedidoBar(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer)
    itens = db.Column(db.Text)
    valor_total = db.Column(db.Float)
    pago = db.Column(db.Boolean, default=False)
    entregue = db.Column(db.Boolean, default=False)
    qrcode_pedido = db.Column(db.String(100))

# --- FERRAMENTAS ---
def gerar_qr_base64(conteudo):
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(conteudo)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

# --- ROTAS DE SISTEMA (RESET E WEBHOOK) ---
@app.route('/reset-bruto-bafafa')
def reset_bruto():
    db.drop_all()
    db.create_all()
    db.session.add(Equipe(nome='Wagner Master', usuario='wagner', senha='123', cargo='admin'))
    db.session.commit()
    return "✅ SISTEMA RESETADO! Tabelas recriadas e Wagner restaurado."

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    if data and data.get("type") == "payment":
        payment_info = sdk.payment().get(data["data"]["id"])
        if payment_info["response"].get("status") == "approved":
            c = Cliente.query.filter_by(payment_id=str(data["data"]["id"])).first()
            if c:
                c.pago = True
                db.session.commit()
    return "", 200

# --- FLUXO DO CLIENTE ---
@app.route('/')
def index(): return render_template('index.html')

@app.route('/reservar', methods=['POST'])
def reservar():
    valor = float(request.form.get('valor_ingresso', 45.0))
    c = Cliente(nome=request.form.get('nome', '').upper().strip(), telefone=request.form.get('telefone', ''), valor_total=valor)
    db.session.add(c); db.session.commit()
    return redirect(url_for('pagamento', id=c.id))

@app.route('/pagamento/<int:id>')
def pagamento(id):
    c = Cliente.query.get_or_404(id)
    tipo = request.args.get('tipo', 'pix')
    res = sdk.payment().create({
        "transaction_amount": c.valor_total, "description": "Bafafá 2026", "payment_method_id": tipo,
        "notification_url": url_for('webhook', _external=True), "payer": {"email": "vendas@bafafa.com"}
    })
    c.payment_id = str(res["response"]["id"]); c.metodo = tipo; db.session.commit()
    qr_c = res["response"]["point_of_interaction"]["transaction_data"]["qr_code"] if tipo == 'pix' else res["response"]["init_point"]
    return render_template('pagamento.html', c=c, qr_img=gerar_qr_base64(qr_c), tipo=tipo)

@app.route('/ingresso/<int:id>')
def ingresso(id):
    c = Cliente.query.get_or_404(id)
    if not c.pago: return render_template('templates-feedback.html', c=c)
    return render_template('obrigado.html', c=c)

# --- FLUXO DE EQUIPE E GESTÃO ---
@app.route('/login-staff', methods=['GET', 'POST'])
def login_staff():
    if request.method == 'POST':
        f = Equipe.query.filter_by(usuario=request.form.get('username'), senha=request.form.get('senha')).first()
        if f:
            cargos_acesso = ['admin', 'gerente', 'produtor', 'portaria', 'bar']
            if f.cargo not in cargos_acesso:
                return "<h1>Acesso Negado</h1><p>Cargo apenas para registro financeiro.</p>"
            session.update({'staff_id': f.id, 'cargo': f.cargo, 'usuario_nome': f.nome})
            if f.cargo in ['admin', 'gerente', 'produtor']: return redirect(url_for('admin_total'))
            if f.cargo == 'portaria': return redirect(url_for('portaria'))
            if f.cargo == 'bar': return redirect(url_for('gestao_bar_staff'))
    return render_template('login_staff.html')

@app.route('/confirmar-direto/<int:id>')
def confirmar_direto(id):
    if session.get('cargo') not in ['admin', 'gerente', 'produtor']:
        return jsonify({"status": "erro"}), 403
    c = Cliente.query.get_or_404(id)
    c.pago = True
    c.metodo = request.args.get('m', 'VIP').upper()
    c.quem_liberou = session.get('usuario_nome')
    db.session.commit()
    return jsonify({"status": "sucesso", "nome": c.nome, "metodo": c.metodo})

@app.route('/admin_total', methods=['GET', 'POST'])
def admin_total():
    if session.get('cargo') not in ['admin', 'gerente', 'produtor']: return redirect(url_for('login_staff'))
    if request.method == 'POST':
        if 'add_staff' in request.form:
            db.session.add(Equipe(nome=request.form.get('n'), usuario=request.form.get('u'), senha=request.form.get('s'), cargo=request.form.get('c'), cachet=float(request.form.get('v') or 0)))
        elif 'add_prod' in request.form:
            db.session.add(Produto(nome=request.form.get('n'), preco_venda=float(request.form.get('v')), estoque=int(request.form.get('e'))))
        db.session.commit()
    
    equipe = Equipe.query.all()
    prods = Produto.query.all()
    pendentes = Cliente.query.filter_by(pago=False).all()
    lucro = (db.session.query(func.sum(Cliente.valor_total)).filter(Cliente.pago == True).scalar() or 0)
    return render_template('admin_total.html', fin={"lucro": lucro, "pendentes": pendentes}, equipe=equipe, produtos=prods)

if __name__ == '__main__':
    with app.app_context(): db.create_all()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))