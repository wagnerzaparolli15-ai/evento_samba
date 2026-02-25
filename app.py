import os, mercadopago, qrcode, io, base64
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func

app = Flask(__name__)

# --- INFRAESTRUTURA ---
db_url = os.getenv("DATABASE_URL")
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url or "sqlite:///bafafa_2026.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.getenv("SECRET_KEY", "BAFAFA_CORP_2026")

db = SQLAlchemy(app)
sdk = mercadopago.SDK(os.getenv("MP_ACCESS_TOKEN"))

# --- MODELOS ---
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

# --- ROTAS DE VENDAS ---
@app.route('/')
def index(): return render_template('index.html')

@app.route('/reservar', methods=['POST'])
def reservar():
    c = Cliente(nome=request.form.get('nome').upper(), telefone=request.form.get('telefone'))
    db.session.add(c); db.session.commit()
    return redirect(url_for('pagamento', id=c.id))

@app.route('/pagamento/<int:id>')
def pagamento(id):
    c = Cliente.query.get_or_404(id)
    try:
        # Lógica simplificada para geração de QR Code
        qr_pix = "00020126360014br.gov.bcb.pix..." # Exemplo de String Pix
        img = qrcode.make(qr_pix); buf = io.BytesIO(); img.save(buf, format="PNG")
        return render_template('pagamento.html', c=c, qr_img=base64.b64encode(buf.getvalue()).decode(), tipo="pix")
    except: return render_template('templates-feedback.html', msg="Erro ao gerar PIX", tipo="erro")

@app.route('/ingresso/<int:id>')
def ingresso(id):
    c = Cliente.query.get_or_404(id)
    if not c.pago: 
        return render_template('templates-feedback.html', tipo='aguardando', c=c)
    return render_template('obrigado.html', c=c)

# --- ROTAS STAFF ---
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
    # Lógica de POST para equipe, produto e custos...
    total_entradas = db.session.query(func.sum(Cliente.valor_total)).filter(Cliente.pago==True).scalar() or 0
    total_custos = db.session.query(func.sum(CustoOperacional.valor)).scalar() or 0
    return render_template('admin_total.html', total_entradas=total_entradas, total_custos=total_custos, 
                           produtos=Produto.query.all(), clientes_pendentes=Cliente.query.filter_by(pago=False).all())

# --- TRATAMENTO DE ERRO 404 ---
@app.errorhandler(404)
def page_not_found(e):
    return render_template('templates-feedback.html', msg="Página não encontrada ou Link Expirado", tipo="erro"), 404

if __name__ == '__main__':
    with app.app_context(): db.create_all()
    app.run(host='0.0.0.0', port=10000)