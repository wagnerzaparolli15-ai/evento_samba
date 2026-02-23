import os, re, mercadopago
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from functools import wraps

app = Flask(__name__)
app.secret_key = "BAFAFA_SISTEMA_2026_FINAL"

# --- 1. CONFIGURAÇÃO DO BANCO DE DADOS (PostgreSQL Render) ---
uri = "postgresql://db_fazcomfe_user:bo24NlcJANvGehkj97PytDoNyoiT696V@dpg-d6b4mq4hncsc7386sfag-a/db_fazcomfe?sslmode=require"
app.config['SQLALCHEMY_DATABASE_URI'] = uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- 2. MERCADO PAGO SDK ---
sdk = mercadopago.SDK("APP_USR-3244228687878580-021915-5528b1d97c9055fab65127d73dc1427d-24221819")

# --- 3. MODELOS (Alinhados 100% com os HTMLs) ---
class Equipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100))
    usuario = db.Column(db.String(50), unique=True)
    senha = db.Column(db.String(50))
    cargo = db.Column(db.String(30)) 
    cachet = db.Column(db.Float, default=0.0)

class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100))
    telefone = db.Column(db.String(20))
    pago = db.Column(db.Boolean, default=False)
    na_casa = db.Column(db.Boolean, default=False) 
    payment_id = db.Column(db.String(100))
    quem_liberou = db.Column(db.String(50), default="") 

class Produto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100))
    preco_custo = db.Column(db.Float, default=0.0)
    preco_venda = db.Column(db.Float, default=0.0)
    estoque = db.Column(db.Integer, default=0)
    vendidos = db.Column(db.Integer, default=0)

# --- 4. FLUXO DO CLIENTE (Reserva e Pagamento) ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/reservar', methods=['POST'])
def reservar():
    nome_raw = request.form.get('nome', '')
    telefone_raw = request.form.get('telefone', '')
    
    if not nome_raw:
        return redirect(url_for('index'))
        
    nome = nome_raw.upper().strip()
    telefone = re.sub(r"\D", "", telefone_raw)
    
    c = Cliente(nome=nome, telefone=telefone)
    db.session.add(c)
    db.session.commit()
    return redirect(url_for('pagamento', id=c.id))

@app.route('/pagamento/<int:id>')
def pagamento(id):
    c = Cliente.query.get_or_404(id)
    try:
        res = sdk.payment().create({
            "transaction_amount": 45.0, "description": "Ingresso Bafafá",
            "payment_method_id": "pix", "payer": {"email": "vendas@bafafa.com"}
        })
        pix = res["response"]["point_of_interaction"]["transaction_data"]
        c.payment_id = str(res["response"]["id"])
        db.session.commit()
        return render_template('pagamento.html', c=c, pix_codigo=pix["qr_code"], qrcode_base64=pix["qr_code_base64"])
    except Exception as e:
        return "Erro na geração do PIX. Tente novamente mais tarde."

@app.route('/ingresso/<int:id>')
def ingresso(id):
    c = Cliente.query.get_or_404(id)
    if not c.pago:
        try:
            p_res = sdk.payment().get(c.payment_id)
            if p_res.get("response", {}).get("status") == "approved":
                c.pago = True
                db.session.commit()
            else:
                return render_template('templates-feedback.html', id=id)
        except:
            return render_template('templates-feedback.html', id=id)
            
    checkin_url = url_for('validar_entrada', id=c.id, _external=True)
    return render_template('obrigado.html', c=c, checkin_url=checkin_url)

# --- 5. GESTÃO DE EQUIPE (Login, Portaria e Bar) ---
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
    clientes = Cliente.query.filter_by(pago=True).order_by(Cliente.na_casa.asc()).all()
    return render_template('portaria.html', clientes=clientes)

@app.route('/validar-entrada/<int:id>')
def validar_entrada(id):
    if 'staff_id' not in session: return redirect(url_for('login_staff'))
    c = Cliente.query.get_or_404(id)
    c.na_casa = True
    c.quem_liberou = session.get('usuario_nome', 'Sistema')
    db.session.commit()
    return render_template('recepcao.html', c=c)

@app.route('/bar-digital/<int:id>')
def bar_digital(id):
    c = Cliente.query.get_or_404(id)
    if not c.na_casa: return "Acesso negado. Valide sua entrada na portaria.", 403
    produtos = Produto.query.filter(Produto.estoque > 0).all()
    return render_template('bar.html', c=c, produtos=produtos)

@app.route('/comprar_item', methods=['POST'])
def comprar_item():
    data = request.json
    for item in data.get('itens', []):
        p = Produto.query.get(item['id'])
        if p and p.estoque > 0:
            p.estoque -= 1
            p.vendidos += 1
    db.session.commit()
    return jsonify({"status": "success"})

# --- 6. ADMINISTRAÇÃO E CUSTEIO (A Matemática Correta) ---
@app.route('/admin_total', methods=['GET', 'POST'])
def admin_total():
    if session.get('cargo') != 'admin': return redirect(url_for('login_staff'))
    if request.method == 'POST':
        if 'novo_staff' in request.form:
            e = Equipe(nome=request.form.get('nome'), usuario=request.form.get('user'), 
                       senha=request.form.get('pass'), cargo=request.form.get('cargo'),
                       cachet=float(request.form.get('cachet') or 0))
            db.session.add(e)
        if 'id_prod' in request.form:
            p = Produto.query.get(request.form.get('id_prod'))
            p.preco_custo = float(request.form.get('custo', 0))
            p.preco_venda = float(request.form.get('venda', 0))
            p.estoque = int(request.form.get('estoque', 0))
        db.session.commit()

    produtos_db = Produto.query.all()
    receita_ingresso = db.session.query(db.func.count(Cliente.id)).filter(Cliente.pago == True).scalar() * 45.0
    receita_bar = sum([p.preco_venda * p.vendidos for p in produtos_db])
    
    custo_produtos = sum([p.preco_custo * p.vendidos for p in produtos_db])
    custos_equipe = db.session.query(db.func.sum(Equipe.cachet)).scalar() or 0
    
    receita_total = receita_ingresso + receita_bar
    despesas_totais = custos_equipe + custo_produtos
    
    fin = {
        "receita": receita_total, 
        "despesas": despesas_totais, 
        "lucro": receita_total - despesas_totais
    }
    
    return render_template('admin_total.html', equipe=Equipe.query.all(), produtos=produtos_db, clientes=Cliente.query.all(), fin=fin)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# --- 7. INICIALIZAÇÃO E RESET TOTAL ---
if __name__ == '__main__':
    with app.app_context():
        db.drop_all()  # <=== DELETANDO O BANCO VELHO (SEM HASHTAG)
        db.create_all() # <=== RECRIANDO O BANCO NOVO
        if not Equipe.query.filter_by(usuario='wagner').first():
            db.session.add(Equipe(nome='Wagner Master', usuario='wagner', senha='123', cargo='admin', cachet=0))
            db.session.commit()
    app.run(host='0.0.0.0', port=10000)