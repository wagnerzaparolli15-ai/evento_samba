import os, mercadopago, qrcode, io, base64
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func

app = Flask(__name__)

# --- CONFIGURAÇÃO ---
db_url = os.getenv("DATABASE_URL")
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url or "sqlite:///bafafa_2026.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.getenv("SECRET_KEY", "BAFAFA_MASTER_KEY_2026_TOTAL")

db = SQLAlchemy(app)
sdk = mercadopago.SDK(os.getenv("MP_ACCESS_TOKEN"))

# --- MODELOS ---
class Equipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100)); usuario = db.Column(db.String(50), unique=True)
    senha = db.Column(db.String(50)); cargo = db.Column(db.String(30))

class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True); nome = db.Column(db.String(100)); telefone = db.Column(db.String(20))
    pago = db.Column(db.Boolean, default=False); na_casa = db.Column(db.Boolean, default=False)
    valor_total = db.Column(db.Float, default=45.0)

class CustoOperacional(db.Model):
    id = db.Column(db.Integer, primary_key=True); descricao = db.Column(db.String(100)); valor = db.Column(db.Float)

# --- AUXILIARES ---
def gerar_qr_b64(conteudo):
    qr = qrcode.make(conteudo)
    buf = io.BytesIO()
    qr.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()

# --- ROTAS PÚBLICAS ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/pagamento/<int:id>')
def pagamento(id):
    c = Cliente.query.get_or_404(id)
    if c.pago: return redirect(url_for('ingresso', id=c.id))
    try:
        pay_data = {"transaction_amount": 45.0, "description": "Ingresso Bafafá", "payment_method_id": "pix", "payer": {"email": "vendas@bafafa.com"}}
        res = sdk.payment().create(pay_data)
        qr_pix = res["response"]["point_of_interaction"]["transaction_data"]["qr_code"]
        return render_template('pagamento.html', c=c, qr_img=gerar_qr_b64(qr_pix), pix_copia_cola=qr_pix)
    except:
        return "Erro ao gerar PIX. Tente novamente."

@app.route('/ingresso/<int:id>')
def ingresso(id):
    c = Cliente.query.get_or_404(id)
    if not c.pago: return redirect(url_for('pagamento', id=c.id))
    qr_checkin = gerar_qr_b64(f"https://evento-samba.onrender.com/validar-entrada/{c.id}")
    return render_template('obrigado.html', c=c, qr_checkin=qr_checkin)

# --- ROTAS DE LOGIN E ACESSO ---
@app.route('/login-staff', methods=['GET', 'POST'])
def login_staff():
    if request.method == 'POST':
        u = Equipe.query.filter_by(usuario=request.form.get('username'), senha=request.form.get('senha')).first()
        if u:
            session.update({'cargo': u.cargo, 'usuario_nome': u.nome})
            if u.cargo in ['admin', 'gerente']: return redirect(url_for('admin_total'))
            return f"<h1>Bem-vindo, {u.nome}! Use o celular para ler os QR Codes.</h1>"
        return "<h1>Usuário ou Senha Incorretos</h1> <a href='/login-staff'>Tentar de novo</a>"
    return render_template('login_staff.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_staff'))

# --- ROTAS STAFF / ADMIN ---
@app.route('/validar-entrada/<int:id>')
def validar_entrada(id):
    if 'cargo' not in session: return redirect(url_for('login_staff'))
    c = Cliente.query.get_or_404(id)
    c.na_casa = True; db.session.commit()
    return f"<body style='background:black;color:lime;text-align:center;'><h1>✅ ENTRADA LIBERADA: {c.nome}</h1><a href='/admin_total'>Voltar</a></body>"

@app.route('/admin_total', methods=['GET', 'POST'])
def admin_total():
    if session.get('cargo') not in ['admin', 'gerente']: return redirect(url_for('login_staff'))
    if request.method == 'POST':
        tipo = request.form.get('form_tipo')
        if tipo == 'equipe':
            db.session.add(Equipe(nome=request.form.get('n'), usuario=request.form.get('u'), senha=request.form.get('s'), cargo=request.form.get('c')))
        elif tipo == 'custo':
            db.session.add(CustoOperacional(descricao=request.form.get('d'), valor=float(request.form.get('v'))))
        db.session.commit()
    
    entradas = db.session.query(func.sum(Cliente.valor_total)).filter_by(pago=True).scalar() or 0
    custos = db.session.query(func.sum(CustoOperacional.valor)).scalar() or 0
    return render_template('admin_total.html', total_entradas=entradas, total_custos=custos, 
                           equipe=Equipe.query.all(), clientes_pendentes=Cliente.query.filter_by(pago=False).all())

@app.route('/aprovar-manual/<int:id>')
def aprovar_manual(id):
    if session.get('cargo') not in ['admin', 'gerente']: return redirect(url_for('login_staff'))
    c = Cliente.query.get_or_404(id); c.pago = True; db.session.commit()
    return redirect(url_for('admin_total'))

@app.route('/reset-bruto-bafafa')
def reset():
    db.drop_all(); db.create_all()
    db.session.add(Equipe(nome='Wagner Master', usuario='wagner', senha='123', cargo='admin'))
    db.session.commit()
    return "✅ SISTEMA REINICIADO COM SUCESSO!"

if __name__ == '__main__':
    with app.app_context(): db.create_all()
    app.run(host='0.0.0.0', port=10000)