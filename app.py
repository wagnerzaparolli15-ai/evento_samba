import os, mercadopago, datetime, qrcode, io, base64
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func

app = Flask(__name__)

# --- 1. CONFIGURAÇÃO (CONEXÃO E SEGURANÇA) ---
db_url = os.getenv("DATABASE_URL")
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
if db_url and "sslmode" not in db_url:
    db_url += "?sslmode=require"

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.getenv("SECRET_KEY", "SISTEMA_BAFAFA_2026_MASTER_TOTAL")

db = SQLAlchemy(app)
sdk = mercadopago.SDK(os.getenv("MP_ACCESS_TOKEN"))

# --- 2. MODELOS (TODA A ESTRUTURA QUE CRIAMOS) ---
class Equipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100)); usuario = db.Column(db.String(50), unique=True)
    senha = db.Column(db.String(50)); cargo = db.Column(db.String(30)); cachet = db.Column(db.Float, default=0.0)

class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True); nome = db.Column(db.String(100)); telefone = db.Column(db.String(20))
    pago = db.Column(db.Boolean, default=False); na_casa = db.Column(db.Boolean, default=False)
    metodo = db.Column(db.String(20), default="pix") # pix, dinheiro, cartao_manual
    payment_id = db.Column(db.String(100)); valor_total = db.Column(db.Float, default=45.0)
    quem_liberou = db.Column(db.String(50), default=""); hora_entrada = db.Column(db.String(20))

class CustoEvento(db.Model): # Controle de Aluguel, Gelo, etc.
    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(100)); valor = db.Column(db.Float, default=0.0)

class Produto(db.Model): # Gestão do Bar
    id = db.Column(db.Integer, primary_key=True); nome = db.Column(db.String(100))
    preco_custo = db.Column(db.Float, default=0.0); preco_venda = db.Column(db.Float, default=0.0)
    estoque = db.Column(db.Integer, default=0); vendidos = db.Column(db.Integer, default=0)

with app.app_context():
    db.create_all()

# --- 3. BIBLIOTECA DE QR CODE LOCAL (ANTI-TRAVAMENTO) ---
def gerar_qr_base64(conteudo):
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(conteudo)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

# --- 4. ROTA DE EMERGÊNCIA (RESET DE BANCO) ---
@app.route('/reset-bruto-bafafa')
def reset_bruto():
    db.drop_all()
    db.create_all()
    db.session.add(Equipe(nome='Wagner Master', usuario='wagner', senha='123', cargo='admin'))
    db.session.commit()
    return "<h1>BANCO RECONSTRUÍDO!</h1><p>Tabelas criadas do zero. Login 'wagner' restaurado.</p>"

# --- 5. FLUXO DO CLIENTE (VENDA E INGRESSO) ---
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
    valor_f = 45.0 * 1.10 if tipo == 'card' else 45.0 # Taxa de 10% no cartão
    try:
        res = sdk.payment().create({
            "transaction_amount": float(valor_f), "description": "Ingresso Bafafá",
            "payment_method_id": tipo, "payer": {"email": "vendas@bafafa.com"}
        })
        conteudo = res["response"]["point_of_interaction"]["transaction_data"]["qr_code"] if tipo == 'pix' else res["response"]["init_point"]
        qr_img = gerar_qr_base64(conteudo)
        c.payment_id = str(res["response"]["id"]); c.valor_total = valor_f; c.metodo = tipo
        db.session.commit()
        return render_template('pagamento.html', c=c, qr_img=qr_img, tipo=tipo)
    except: return "Erro ao conectar com Mercado Pago.", 500

@app.route('/ingresso/<int:id>')
def ingresso(id):
    c = Cliente.query.get_or_404(id)
    if not c.pago and c.metodo == "pix":
        p_res = sdk.payment().get(c.payment_id)
        if p_res["response"].get("status") == "approved":
            c.pago = True; db.session.commit()
    return render_template('obrigado.html', c=c, checkin_url=url_for('validar_entrada', id=c.id, _external=True))

# --- 6. GESTÃO E PORTARIA (STAFF) ---
@app.route('/login-staff', methods=['GET', 'POST'])
def login_staff():
    if request.method == 'POST':
        f = Equipe.query.filter_by(usuario=request.form.get('username'), senha=request.form.get('senha')).first()
        if f:
            session.update({'staff_id': f.id, 'cargo': f.cargo, 'usuario_nome': f.nome})
            return redirect(url_for('admin_total' if f.cargo == 'admin' else 'portaria'))
    return render_template('login_staff.html')

@app.route('/confirmar-manual/<int:id>')
def confirmar_manual(id):
    if 'staff_id' not in session: return redirect(url_for('login_staff'))
    c = Cliente.query.get_or_404(id)
    c.pago = True; c.metodo = request.args.get('m', 'manual'); db.session.commit()
    return redirect(url_for('validar_entrada', id=c.id))

@app.route('/validar-entrada/<int:id>')
def validar_entrada(id):
    if 'staff_id' not in session: return redirect(url_for('login_staff'))
    c = Cliente.query.get_or_404(id)
    if c.pago and not c.na_casa:
        c.na_casa = True; c.quem_liberou = session['usuario_nome']
        c.hora_entrada = datetime.datetime.now().strftime("%H:%M"); db.session.commit()
    return render_template('recepcao.html', c=c)

# --- 7. ADMINISTRAÇÃO ANALÍTICA TOTAL ---
@app.route('/admin_total', methods=['GET', 'POST'])
def admin_total():
    if session.get('cargo') != 'admin': return redirect(url_for('login_staff'))
    if request.method == 'POST':
        if 'add_custo' in request.form:
            db.session.add(CustoEvento(descricao=request.form.get('d'), valor=float(request.form.get('v') or 0)))
        elif 'add_prod' in request.form:
            db.session.add(Produto(nome=request.form.get('n'), preco_custo=float(request.form.get('c') or 0), preco_venda=float(request.form.get('v') or 0), estoque=int(request.form.get('e') or 0)))
        elif 'add_equipe' in request.form:
            db.session.add(Equipe(nome=request.form.get('nome'), usuario=request.form.get('usuario'), senha=request.form.get('senha'), cargo=request.form.get('cargo'), cachet=float(request.form.get('cachet') or 0)))
        db.session.commit()

    prods = Produto.query.all()
    # Soma de vendas real com proteção contra erro 500
    try:
        rec_ingressos = db.session.query(func.sum(Cliente.valor_total)).filter(Cliente.pago == True).scalar() or 0
    except: rec_ingressos = 0
    
    rec_bar = sum([p.preco_venda * p.vendidos for p in prods])
    custos_fixos = (db.session.query(func.sum(CustoEvento.valor)).scalar() or 0) + (db.session.query(func.sum(Equipe.cachet)).scalar() or 0)
    
    fin = {
        "lucro": (rec_ingressos + rec_bar) - custos_fixos,
        "na_casa": Cliente.query.filter_by(na_casa=True).count(),
        "pendentes": Cliente.query.filter_by(pago=False).all()
    }
    return render_template('admin_total.html', fin=fin, produtos=prods, equipe=Equipe.query.all(), custos=CustoEvento.query.all())

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)