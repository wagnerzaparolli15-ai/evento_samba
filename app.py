import os, mercadopago, qrcode, io, base64
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func

app = Flask(__name__)

# --- INFRAESTRUTURA (CONFIGURAÇÃO DE MULTINACIONAL) ---
db_url = os.getenv("DATABASE_URL")
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url or "sqlite:///bafafa_2026.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.getenv("SECRET_KEY", "BAFAFA_CORP_MASTER_2026")

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
    metodo = db.Column(db.String(20), default="pix"); valor_total = db.Column(db.Float, default=45.0)

class Produto(db.Model):
    id = db.Column(db.Integer, primary_key=True); nome = db.Column(db.String(100))
    imagem = db.Column(db.String(100)); preco_venda = db.Column(db.Float, default=0.0); estoque = db.Column(db.Integer, default=0)

class CustoOperacional(db.Model):
    id = db.Column(db.Integer, primary_key=True); descricao = db.Column(db.String(100)); valor = db.Column(db.Float)

# --- ROTAS DE VENDAS (CLIENTE) ---
@app.route('/')
def index(): return render_template('index.html')

@app.route('/reservar', methods=['POST'])
def reservar():
    n = request.form.get('nome') or request.form.get('n')
    t = request.form.get('telefone') or request.form.get('t')
    c = Cliente(nome=n.upper(), telefone=t)
    db.session.add(c); db.session.commit()
    return redirect(url_for('pagamento', id=c.id))

@app.route('/pagamento/<int:id>')
def pagamento(id):
    c = Cliente.query.get_or_404(id)
    try:
        # Tenta gerar o Pix Real via Mercado Pago
        res = sdk.payment().create({"transaction_amount": 45.0, "description": "Bafafá 2026", "payment_method_id": "pix", "payer": {"email": "vendas@bafafa.com"}})
        qr_pix = res["response"]["point_of_interaction"]["transaction_data"]["qr_code"]
        img = qrcode.make(qr_pix); buf = io.BytesIO(); img.save(buf, format="PNG")
        return render_template('pagamento.html', c=c, qr_img=base64.b64encode(buf.getvalue()).decode(), pix_copia_cola=qr_pix)
    except: 
        # Se falhar o MP, mostra tela de aguardando/erro
        return render_template('templates-feedback.html', tipo='erro', msg="Erro ao gerar PIX. Tente novamente.")

@app.route('/ingresso/<int:id>')
def ingresso(id):
    c = Cliente.query.get_or_404(id)
    if not c.pago: return render_template('templates-feedback.html', tipo='aguardando', c=c)
    return render_template('obrigado.html', c=c)

# --- ROTAS STAFF & ADMIN ---
@app.route('/login-staff', methods=['GET', 'POST'])
def login_staff():
    if request.method == 'POST':
        u = Equipe.query.filter_by(usuario=request.form.get('username'), senha=request.form.get('senha')).first()
        if u:
            session.update({'cargo': u.cargo, 'usuario_nome': u.nome})
            return redirect(url_for('admin_total' if u.cargo in ['admin', 'gerente'] else 'portaria'))
    return render_template('login_staff.html')

@app.route('/admin_total', methods=['GET', 'POST'])
def admin_total():
    if session.get('cargo') not in ['admin', 'gerente']: return redirect(url_for('login_staff'))
    
    if request.method == 'POST':
        tipo = request.form.get('form_tipo')
        if tipo == 'equipe':
            db.session.add(Equipe(nome=request.form.get('n'), usuario=request.form.get('u'), senha=request.form.get('s'), cargo=request.form.get('c'), cachet=float(request.form.get('v') or 0)))
        elif tipo == 'produto':
            db.session.add(Produto(nome=request.form.get('n'), preco_venda=float(request.form.get('pv') or 0), estoque=int(request.form.get('e') or 0), imagem=request.form.get('img')))
        elif tipo == 'custo':
            db.session.add(CustoOperacional(descricao=request.form.get('d'), valor=float(request.form.get('v') or 0)))
        db.session.commit()

    entradas = db.session.query(func.sum(Cliente.valor_total)).filter(Cliente.pago==True).scalar() or 0
    saidas = (db.session.query(func.sum(CustoOperacional.valor)).scalar() or 0) + (db.session.query(func.sum(Equipe.cachet)).scalar() or 0)
    
    return render_template('admin_total.html', total_entradas=entradas, total_custos=saidas, 
                           produtos=Produto.query.all(), equipe=Equipe.query.all(),
                           clientes_pendentes=Cliente.query.filter_by(pago=False).all())

@app.route('/portaria')
def portaria():
    if session.get('cargo') not in ['admin', 'portaria']: return redirect(url_for('login_staff'))
    return render_template('portaria.html', clientes=Cliente.query.filter_by(pago=True, na_casa=False).all())

@app.route('/validar-entrada/<int:id>')
def validar_entrada(id):
    c = Cliente.query.get_or_404(id)
    c.na_casa = True; db.session.commit()
    return render_template('recepcao.html', c=c)

@app.route('/bar-digital/<int:id>')
def bar_digital(id):
    c = Cliente.query.get_or_404(id)
    return render_template('bar.html', c=c, produtos=Produto.query.filter(Produto.estoque > 0).all())

# --- ROTA DE ATIVAÇÃO / RESET (A QUE ESTAVA DANDO ERRO) ---
@app.route('/reset-bruto-bafafa')
def reset():
    try:
        db.drop_all(); db.create_all()
        admin = Equipe(nome='Wagner Master', usuario='wagner', senha='123', cargo='admin')
        db.session.add(admin); db.session.commit()
        return "✅ SUCESSO! Banco resetado. Login: wagner / 123 <br><a href='/login-staff'>Ir para Login</a>"
    except Exception as e:
        return f"❌ Erro: {str(e)}"

@app.route('/logout')
def logout():
    session.clear(); return redirect(url_for('login_staff'))

if __name__ == '__main__':
    with app.app_context(): db.create_all()
    app.run(host='0.0.0.0', port=10000)