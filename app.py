import os, re, mercadopago
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text, inspect
from functools import wraps
from datetime import datetime

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.secret_key = "segredo_bafafa_2026_ESTABILIDADE_TOTAL"

# --- BANCO DE DADOS ---
uri = "postgresql://db_fazcomfe_user:bo24NlcJANvGehkj97PytDoNyoiT696V@dpg-d6b4mq4hncsc7386sfag-a/db_fazcomfe?sslmode=require"
app.config['SQLALCHEMY_DATABASE_URI'] = uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- MERCADO PAGO ---
sdk = mercadopago.SDK("APP_USR-3244228687878580-021915-5528b1d97c9055fab65127d73dc1427d-24221819")

# --- MODELOS (ESTRUTURA COMPLETA) ---
class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    senha = db.Column(db.String(50), nullable=False)
    cargo = db.Column(db.String(30)) 

class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100))
    telefone = db.Column(db.String(20), unique=True)
    pago = db.Column(db.Boolean, default=False)
    utilizado = db.Column(db.Boolean, default=False)
    quem_liberou = db.Column(db.String(50))
    data_entrada = db.Column(db.DateTime)
    payment_id = db.Column(db.String(100))

class Produto(db.Model):
    __tablename__ = 'bar_produtos'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    preco_custo = db.Column(db.Float, default=0.0)
    preco_venda = db.Column(db.Float, default=0.0)
    estoque_inicial = db.Column(db.Integer, default=0)
    vendido = db.Column(db.Integer, default=0)
    imagem_local = db.Column(db.String(100))

# --- SINCRONIZAÇÃO TOTAL (CORREÇÃO DE ERROS DE BANCO) ---
def sincronizar_sistema():
    with app.app_context():
        # Deleta a tabela antiga para eliminar colunas fantasmas (como a 'preco')
        try:
            db.session.execute(text("DROP TABLE IF EXISTS bar_produtos CASCADE"))
            db.session.commit()
        except Exception:
            db.session.rollback()

        # Reconstrói com a estrutura certa e interligada
        db.create_all()

        if not Produto.query.first():
            lista = [
                Produto(nome='Antarctica Lata (fardo 18)', imagem_local='antarctica.jpg'),
                Produto(nome='Brahma Lata (fardo 18)', imagem_local='brahma.jpg'),
                Produto(nome='Heineken 350ml (fardo 12)', imagem_local='heineken.jpg'),
                Produto(nome='Amstel 473ml (fardo 12)', imagem_local='amstel.jpg'),
                Produto(nome='Spaten 350ml (fardo 12)', imagem_local='spaten.jpg'),
                Produto(nome='Coca-Cola Lata (fardo 12)', imagem_local='coca.jpg'),
                Produto(nome='Guaraná Ant. (fardo 12)', imagem_local='guarana.jpg'),
                Produto(nome='Red Bull (fardo 24)', imagem_local='redbull.jpg'),
                Produto(nome='Red Label (Unidade)', imagem_local='redlabel.jpg'),
                Produto(nome='Black Label (Unidade)', imagem_local='blacklabel.jpg')
            ]
            db.session.add_all(lista)
            db.session.commit()
        
        if not Usuario.query.filter_by(username='wagner').first():
            db.session.add(Usuario(username='wagner', senha='123', cargo='admin'))
            db.session.commit()

sincronizar_sistema()

# --- SEGURANÇA E ACESSOS ---
def login_obrigatorio(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session: return redirect(url_for('login_staff'))
        return f(*args, **kwargs)
    return decorated_function

# --- ROTAS STAFF ---
@app.route('/login-staff', methods=['GET', 'POST'])
def login_staff():
    if request.method == 'POST':
        user = Usuario.query.filter_by(username=request.form.get('username'), senha=request.form.get('senha')).first()
        if user:
            session.update({'usuario_id': user.id, 'usuario_nome': user.username, 'usuario_cargo': user.cargo})
            destinos = {'admin': 'admin_evento', 'portaria': 'painel_portaria', 'bar': 'painel_barman'}
            return redirect(url_for(destinos.get(user.cargo, 'login_staff')))
    return render_template('login_staff.html')

@app.route('/admin/evento', methods=['GET', 'POST'])
@login_obrigatorio
def admin_evento():
    if session.get('usuario_cargo') != 'admin': return redirect(url_for('login_staff'))
    if request.method == 'POST':
        if 'id_prod' in request.form:
            p = Produto.query.get(request.form.get('id_prod'))
            p.preco_custo = float(request.form.get('custo') or 0)
            p.preco_venda = float(request.form.get('venda') or 0)
            p.estoque_inicial = int(request.form.get('estoque') or 0)
            db.session.commit()
        return redirect(url_for('admin_evento'))
    produtos = Produto.query.all()
    c_tot = sum([p.preco_custo * p.estoque_inicial for p in produtos])
    lucro = sum([(p.preco_venda - p.preco_custo) * p.estoque_inicial for p in produtos])
    return render_template('admin_bar.html', produtos=produtos, custo_total=c_tot, lucro=lucro, staff=Usuario.query.all())

@app.route('/admin/reset-total', methods=['POST'])
@login_obrigatorio
def reset_total():
    if session.get('usuario_cargo') != 'admin': return "Negado"
    db.session.query(Cliente).delete()
    for p in Produto.query.all(): p.vendido = 0
    db.session.commit()
    return redirect(url_for('admin_evento'))

@app.route('/painel-portaria')
@login_obrigatorio
def painel_portaria():
    return render_template('portaria.html', clientes=Cliente.query.order_by(Cliente.id.desc()).all())

@app.route('/valida-portaria/<int:id>')
@login_obrigatorio
def valida_portaria(id):
    c = Cliente.query.get_or_404(id)
    if c.utilizado: return f"<h1>ERRO: JÁ ENTROU!</h1><p>Liberado por {c.quem_liberou}</p>"
    c.utilizado, c.pago, c.quem_liberou, c.data_entrada = True, True, session['usuario_nome'], datetime.now()
    db.session.commit()
    return redirect(url_for('painel_portaria'))

@app.route('/painel-barman')
@login_obrigatorio
def painel_barman():
    return render_template('gestao_bar.html', produtos=Produto.query.all())

# --- FLUXO CLIENTE ---
@app.route('/')
def index(): return render_template('index.html', preco=45.0)

@app.route('/reservar', methods=['POST'])
def reservar():
    c = Cliente(nome=request.form.get('nome','').upper().strip(), telefone=re.sub(r"\D", "", request.form.get('telefone','')))
    db.session.add(c); db.session.commit()
    return redirect(url_for('pagamento', id=c.id))

@app.route('/pagamento/<int:id>')
def pagamento(id):
    c = Cliente.query.get_or_404(id)
    pay_data = {"transaction_amount": 45.0, "description": f"Bafafá - {c.nome}", "payment_method_id": "pix", "payer": {"email": "wagnerzaparolli15@gmail.com"}}
    result = sdk.payment().create(pay_data)
    pix = result["response"]["point_of_interaction"]["transaction_data"]
    c.payment_id = str(result["response"]["id"]); db.session.commit()
    return render_template('pagamento.html', c=c, pix_codigo=pix["qr_code"], qrcode_base64=pix["qr_code_base64"])

@app.route('/ingresso/<int:id>')
def validar_ingresso(id):
    c = Cliente.query.get_or_404(id)
    url = f"https://evento-samba.onrender.com/valida-portaria/{c.id}"
    return render_template('obrigado.html', c=c, checkin_url=url)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_staff'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))