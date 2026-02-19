import os
import re
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy.exc import IntegrityError

app = Flask(__name__)

# --- CONFIGURAÇÃO DE DATABASE (POSTGRES / SQLITE) ---
uri = os.environ.get('DATABASE_URL')
if uri and uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)
if uri and "sslmode" not in uri:
    uri += "&sslmode=require" if "?" in uri else "?sslmode=require"

app.config['SQLALCHEMY_DATABASE_URI'] = uri or 'sqlite:///fazcomfe.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'faz-com-fe-2026-papo-de-samba')

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# --- MODELO DE DADOS ---
class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    telefone = db.Column(db.String(20), nullable=False, unique=True)
    valor_pago = db.Column(db.Float)
    lote = db.Column(db.Integer)
    compareceu = db.Column(db.Boolean, default=False)

# --- ROTAS ---

@app.route('/')
def index():
    try:
        total = Cliente.query.count()
        # Lógica de lotes: 75 primeiros = R$ 45, depois R$ 55
        preco = 45.0 if total < 75 else 55.0
        lote = 1 if total < 75 else 2
        return render_template('index.html', preco=preco, lote=lote)
    except:
        return render_template('index.html', preco=45.0, lote=1)

@app.route('/comprar', methods=['POST'])
def comprar():
    nome = request.form.get('nome', '').strip().upper()
    tel = request.form.get('telefone', '').strip()
    
    # Limpa o telefone para manter apenas números
    tel_clean = re.sub(r"\D", "", tel)
    
    try:
        total = Cliente.query.count()
        valor, num_lote = (45.0, 1) if total < 75 else (55.0, 2)
        
        if nome and tel_clean:
            novo = Cliente(nome=nome, telefone=tel_clean, valor_pago=valor, lote=num_lote)
            db.session.add(novo)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                # Telefone já existe no banco
                return render_template('index.html', preco=valor, lote=num_lote, error='Este telefone já possui um ingresso registrado.')

            # Gera a URL absoluta para o QR Code
            base_url = os.environ.get('BASE_URL', request.host_url).rstrip('/')
            checkin_url = f"{base_url}{url_for('checkin', id=novo.id)}"

            return render_template('obrigado.html', 
                                 nome=nome, 
                                 id_cliente=novo.id, 
                                 valor=valor, 
                                 checkin_url=checkin_url)
    except Exception as e:
        db.session.rollback()
        return f"Erro ao processar reserva: {str(e)}"
    
    return redirect(url_for('index'))

@app.route('/checkin/<int:id>')
def checkin(id):
    c = Cliente.query.get_or_404(id)
    
    # Lógica de QR Code Único (Trava de Segurança)
    if not c.compareceu:
        c.compareceu = True
        db.session.commit()
        cor = "#2ecc71" # Verde
        status = "✅ ACESSO LIBERADO"
        msg = f"Seja bem-vindo(a), {c.nome}! Sua feijoada está garantida."
    else:
        cor = "#e74c3c" # Vermelho
        status = "❌ ACESSO NEGADO"
        msg = f"ALERTA: O ingresso de {c.nome} já foi utilizado anteriormente!"

    return f"""
    <div style='text-align:center;padding:50px;font-family:sans-serif;background:#000;color:#fff;height:100vh;'>
        <h1 style='color:{cor};font-size:3rem;'>{status}</h1>
        <p style='font-size:1.5rem;'>{msg}</p>
        <br><br>
        <a href='/' style='color:#f1c40f;text-decoration:none;'>Voltar ao Início</a>
    </div>
    """

@app.route('/admin-cara-2026')
def admin():
    clientes = Cliente.query.order_by(Cliente.id.desc()).all()
    faturamento = sum([c.valor_pago for c in clientes if c.valor_pago])
    return render_template('admin.html', clientes=clientes, total=len(clientes), faturamento=faturamento)

if __name__ == '__main__':
    with app.app_context():
        # Cria tabelas se não existirem (não apaga dados existentes)
        db.create_all()
    app.run(debug=True)