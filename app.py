import os
import re
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy.exc import IntegrityError

app = Flask(__name__)

# --- CONFIGURAÇÃO DE DATABASE ---
uri = os.environ.get('DATABASE_URL')
if uri and uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = uri or 'sqlite:///fazcomfe.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'faz-com-fe-2026')

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# --- MODELO ---
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
        preco = 45.0 if total < 75 else 55.0
        lote = 1 if total < 75 else 2
        return render_template('index.html', preco=preco, lote=lote)
    except:
        return render_template('index.html', preco=45.0, lote=1)

@app.route('/comprar', methods=['POST'])
def comprar():
    nome = request.form.get('nome', '').strip().upper()
    tel = request.form.get('telefone', '').strip()
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
                return render_template('index.html', preco=valor, lote=num_lote, error='Telefone já registrado.')

            base_url = os.environ.get('BASE_URL', request.host_url).rstrip('/')
            checkin_url = f"{base_url}{url_for('checkin', id=novo.id)}"
            return render_template('obrigado.html', nome=nome, id_cliente=novo.id, valor=valor, checkin_url=checkin_url)
    except Exception as e:
        db.session.rollback()
        return f"Erro: {str(e)}"
    return redirect(url_for('index'))

@app.route('/checkin/<int:id>')
def checkin(id):
    c = Cliente.query.get_or_404(id)
    if not c.compareceu:
        c.compareceu = True
        db.session.commit()
        return f"<div style='text-align:center;padding:50px;font-family:sans-serif;'> <h1 style='color:green;font-size:3rem;'>✅ LIBERADO: {c.nome}</h1> <p>Aproveite a feijoada!</p> </div>"
    return f"<div style='text-align:center;padding:50px;font-family:sans-serif;'> <h1 style='color:red;font-size:3rem;'>❌ ALERTA: {c.nome} JÁ ENTROU!</h1> <p>Ingresso inválido para reuso.</p> </div>"

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)