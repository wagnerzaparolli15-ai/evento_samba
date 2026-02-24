import os, mercadopago
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func

app = Flask(__name__)

# --- 1. CONFIGURAÇÃO (RENDER) ---
db_url = os.getenv("DATABASE_URL")
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
if db_url and "sslmode" not in db_url:
    db_url += "?sslmode=require"

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.getenv("SECRET_KEY", "BAFAFA_MASTER_2026_TOTAL")

db = SQLAlchemy(app)
sdk = mercadopago.SDK(os.getenv("MP_ACCESS_TOKEN"))

# --- 2. MODELOS (ESTRUTURA SAGRADA) ---
class Equipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100)); usuario = db.Column(db.String(50), unique=True)
    senha = db.Column(db.String(50)); cargo = db.Column(db.String(30)); cachet = db.Column(db.Float, default=0.0)

class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True); nome = db.Column(db.String(100)); telefone = db.Column(db.String(20))
    pago = db.Column(db.Boolean, default=False); na_casa = db.Column(db.Boolean, default=False)
    payment_id = db.Column(db.String(100)); quem_liberou = db.Column(db.String(50), default="")

class Produto(db.Model):
    id = db.Column(db.Integer, primary_key=True); nome = db.Column(db.String(100))
    preco_custo = db.Column(db.Float, default=0.0); preco_venda = db.Column(db.Float, default=0.0)
    estoque = db.Column(db.Integer, default=0); vendidos = db.Column(db.Integer, default=0)

# --- 3. INICIALIZAÇÃO DO BANCO ---
with app.app_context():
    db.create_all()
    if not Equipe.query.filter_by(usuario='wagner').first():
        db.session.add(Equipe(nome='Wagner Master', usuario='wagner', senha='123', cargo='admin', cachet=0))
        db.session.commit()

# --- 4. ROTAS DE VENDA (PIX) ---
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
            "transaction_amount": 45.0, 
            "description": "Ingresso Bafafá", 
            "payment_method_id": "pix", 
            "payer": {"email": "vendas@bafafa.com"}
        })
        pix = res["response"]["point_of_interaction"]["transaction_data"]
        c.payment_id = str(res["response"]["id"]); db.session.commit()
        return render_template('pagamento.html', c=c, pix_codigo=pix["qr_code"], qrcode_base64=pix["qr_code_base64"])
    except: return "Erro ao gerar PIX. Verifique seu Token no Render.", 500

# --- 5. ROTA DO INGRESSO (O QUE TINHA SUMIDO) ---
@app.route('/ingresso/<int:id>')
def ingresso(id):
    c = Cliente.query.get_or_404(id)
    if not c.pago:
        try:
            p_res = sdk.payment().get(c.payment_id)
            if p_res["response"].get("status") == "approved":
                c.pago = True; db.session.commit()
            else:
                return render_template('templates-feedback.html', id=id)
        except: return render_template('templates-feedback.html', id=id)
    return render_template('obrigado.html', c=c, checkin_url=url_for('validar_entrada', id=c.id, _external=True))

# --- 6. STAFF E PORTARIA ---
@app.route('/login-staff', methods=['GET', 'POST'])
def login_staff():
    if request.method == 'POST':
        f = Equipe.query.filter_by(usuario=request.form.get('username'), senha=request.form.get('senha')).first()
        if f:
            session.update({'staff_id': f.id, 'cargo': f.cargo, 'usuario_nome': f.nome})
            return redirect(url_for('admin_total' if f.cargo == 'admin' else 'portaria'))
    return render_template('login_staff.html')

@app.route('/portaria')
def portaria():
    if 'staff_id' not in session: return redirect(url_for('login_staff'))
    clientes = Cliente.query.filter_by(pago=True, na_casa=False).all()
    return render_template('portaria.html', clientes=clientes)

@app.route('/validar-entrada/<int:id>')
def validar_entrada(id):
    if 'usuario_nome' not in session: return redirect(url_for('login_staff'))
    c = Cliente.query.get_or_404(id)
    c.na_casa = True
    c.quem_liberou = session['usuario_nome']
    db.session.commit()
    return render_template('recepcao.html', c=c)

# --- 7. BAR E ESTOQUE ---
@app.route('/bar-digital/<int:id>')
def bar_digital(id):
    c = Cliente.query.get_or_404(id)
    produtos = Produto.query.filter(Produto.estoque > 0).all()
    return render_template('bar.html', c=c, produtos=produtos)

@app.route('/comprar_item', methods=['POST'])
def comprar_item():
    data = request.json
    for item in data.get('itens', []):
        p = Produto.query.get(item['id'])
        if p and p.estoque > 0:
            p.estoque -= 1; p.vendidos += 1
    db.session.commit()
    return jsonify({"status": "success"})

# --- 8. ADMINISTRAÇÃO TOTAL ---
@app.route('/admin_total', methods=['GET', 'POST'])
def admin_total():
    if session.get('cargo') != 'admin': return redirect(url_for('login_staff'))
    
    if request.method == 'POST':
        if 'add_equipe' in request.form:
            db.session.add(Equipe(nome=request.form.get('nome'), usuario=request.form.get('usuario'), senha=request.form.get('senha'), cargo=request.form.get('cargo'), cachet=float(request.form.get('cachet') or 0)))
        elif 'add_produto' in request.form:
            db.session.add(Produto(nome=request.form.get('nome'), preco_custo=float(request.form.get('custo')), preco_venda=float(request.form.get('venda')), estoque=int(request.form.get('estoque'))))
        db.session.commit()

    prod_all = Produto.query.all()
    ingressos_pago = Cliente.query.filter_by(pago=True).count()
    rec_ingresso = ingressos_pago * 45.0
    rec_bar = sum([p.preco_venda * p.vendidos for p in prod_all])
    custo_bar = sum([p.preco_custo * p.vendidos for p in prod_all])
    despesa_equipe = db.session.query(func.sum(Equipe.cachet)).scalar() or 0
    
    fin = {
        "receita": rec_ingresso + rec_bar, 
        "lucro": (rec_ingresso + rec_bar) - (despesa_equipe + custo_bar),
        "na_casa": Cliente.query.filter_by(na_casa=True).count()
    }
    
    return render_template('admin_total.html', equipe=Equipe.query.all(), produtos=prod_all, clientes_na_casa=Cliente.query.filter_by(na_casa=True).all(), fin=fin)

@app.route('/logout')
def logout():
    session.clear(); return redirect(url_for('index'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)