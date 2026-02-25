import os, mercadopago, qrcode, io, base64
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func

app = Flask(__name__)

# --- CONFIGURAÇÃO DE INFRAESTRUTURA ---
db_url = os.getenv("DATABASE_URL")
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url or "sqlite:///bafafa_2026.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.getenv("SECRET_KEY", "BAFAFA_CORP_2026_TOTAL")

db = SQLAlchemy(app)
sdk = mercadopago.SDK(os.getenv("MP_ACCESS_TOKEN"))

# --- MODELOS DE DADOS ---
class Equipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100))
    usuario = db.Column(db.String(50), unique=True)
    senha = db.Column(db.String(50))
    cargo = db.Column(db.String(30)) # 'admin', 'gerente', 'portaria'
    cachet = db.Column(db.Float, default=0.0)

class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100))
    telefone = db.Column(db.String(20))
    pago = db.Column(db.Boolean, default=False)
    na_casa = db.Column(db.Boolean, default=False)
    metodo = db.Column(db.String(20), default="pix")
    valor_total = db.Column(db.Float, default=45.0)

class Produto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100))
    imagem = db.Column(db.String(100))
    preco_custo = db.Column(db.Float, default=0.0)
    preco_venda = db.Column(db.Float, default=0.0)
    estoque = db.Column(db.Integer, default=0)

class CustoOperacional(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(100))
    valor = db.Column(db.Float)

# --- ROTAS ADMINISTRATIVAS (ONDE VOCÊ CADASTRA A EQUIPE) ---

@app.route('/admin_total', methods=['GET', 'POST'])
def admin_total():
    if session.get('cargo') not in ['admin', 'gerente']:
        return redirect(url_for('login_staff'))
    
    if request.method == 'POST':
        tipo = request.form.get('form_tipo')
        
        # LÓGICA DE CADASTRO DE EQUIPE (O QUE VOCÊ VIU NA IMAGEM)
        if tipo == 'equipe':
            nova_pessoa = Equipe(
                nome=request.form.get('n'),
                usuario=request.form.get('u'),
                senha=request.form.get('s'),
                cargo=request.form.get('c'),
                cachet=float(request.form.get('v') or 0)
            )
            db.session.add(nova_pessoa)
        
        # Cadastro de Produtos
        elif tipo == 'produto':
            db.session.add(Produto(nome=request.form.get('n'), preco_custo=float(request.form.get('pc') or 0), preco_venda=float(request.form.get('pv') or 0), estoque=int(request.form.get('e') or 0), imagem=request.form.get('img')))
        
        # Lançamento de Custos
        elif tipo == 'custo':
            db.session.add(CustoOperacional(descricao=request.form.get('d'), valor=float(request.form.get('v') or 0)))
            
        db.session.commit()

    # Cálculos Financeiros
    entradas = db.session.query(func.sum(Cliente.valor_total)).filter(Cliente.pago==True).scalar() or 0
    saidas_op = db.session.query(func.sum(CustoOperacional.valor)).scalar() or 0
    saidas_staff = db.session.query(func.sum(Equipe.cachet)).scalar() or 0
    total_gastos = saidas_op + saidas_staff

    return render_template('admin_total.html', 
                           total_entradas=entradas, 
                           total_custos=total_gastos, 
                           produtos=Produto.query.all(), 
                           equipe=Equipe.query.all(),
                           clientes_pendentes=Cliente.query.filter_by(pago=False).all())

# --- ROTAS DE LOGIN E PORTARIA ---

@app.route('/login-staff', methods=['GET', 'POST'])
def login_staff():
    if request.method == 'POST':
        u = Equipe.query.filter_by(usuario=request.form.get('username'), senha=request.form.get('senha')).first()
        if u:
            session.update({'cargo': u.cargo, 'usuario_nome': u.nome})
            if u.cargo in ['admin', 'gerente']: return redirect(url_for('admin_total'))
            if u.cargo == 'portaria': return redirect(url_for('portaria'))
    return render_template('login_staff.html')

@app.route('/portaria')
def portaria():
    if session.get('cargo') not in ['admin', 'portaria']: return redirect(url_for('login_staff'))
    return render_template('portaria.html', clientes=Cliente.query.filter_by(pago=True, na_casa=False).all())

@app.route('/reset-bruto-bafafa')
def reset():
    db.drop_all(); db.create_all()
    # Wagner como Admin Master
    db.session.add(Equipe(nome='Wagner Master', usuario='wagner', senha='123', cargo='admin', cachet=0))
    db.session.commit()
    return "✅ SISTEMA RESETADO! Use wagner / 123 no login-staff"

# --- FLUXO DO CLIENTE ---
@app.route('/')
def index(): return render_template('index.html')

@app.route('/reservar', methods=['POST'])
def reservar():
    c = Cliente(nome=request.form.get('nome', '').upper().strip(), telefone=request.form.get('telefone', ''))
    db.session.add(c); db.session.commit()
    return redirect(url_for('pagamento', id=c.id))

if __name__ == '__main__':
    with app.app_context(): db.create_all()
    app.run(host='0.0.0.0', port=10000)