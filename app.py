import os
import re
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy.exc import IntegrityError

app = Flask(__name__)

# Configuração da Database
uri = os.environ.get('DATABASE_URL')
if uri and uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = uri or 'sqlite:///fazcomfe.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Migrações
migrate = Migrate(app, db)

# Configurações adicionais
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret')


# Modelo Completo
class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    telefone = db.Column(db.String(20), nullable=False, unique=True)
    valor_pago = db.Column(db.Float)
    lote = db.Column(db.Integer)
    compareceu = db.Column(db.Boolean, default=False)

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
    # Normaliza telefone (mantém apenas dígitos)
    tel_clean = re.sub(r"\D", "", tel)
    try:
        total = Cliente.query.count()
        valor, num_lote = (45.0, 1) if total < 75 else (55.0, 2)
        if nome and tel:
            novo = Cliente(nome=nome, telefone=tel_clean, valor_pago=valor, lote=num_lote)
            db.session.add(novo)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                # Telefone duplicado: retorna mensagem amigável
                return render_template('index.html', preco=valor, lote=num_lote, error='Telefone já registrado.')

            # Construir URL de checkin: usa BASE_URL se definido, senão host atual
            base = os.environ.get('BASE_URL')
            if base:
                base = base.rstrip('/')
                checkin_url = f"{base}{url_for('checkin', id=novo.id)}"
            else:
                checkin_url = url_for('checkin', id=novo.id, _external=True)

            return render_template('obrigado.html', nome=nome, id_cliente=novo.id, valor=valor, checkin_url=checkin_url)
    except Exception as e:
        db.session.rollback()
        return f"Erro ao processar: {str(e)}"
    return redirect(url_for('index'))

@app.route('/checkin/<int:id>')
def checkin(id):
    c = Cliente.query.get_or_404(id)
    if not c.compareceu:
        c.compareceu = True
        db.session.commit()
        return f"<h1>LIBERADO: {c.nome}</h1>"
    return f"<h1>ALERTA: {c.nome} JÁ ENTROU!</h1>"


@app.route('/admin')
def admin():
    clientes = [(c.id, c.nome, c.telefone) for c in Cliente.query.order_by(Cliente.id).all()]
    return render_template('admin.html', clientes=clientes)

if __name__ == '__main__':
    with app.app_context():
        # Cria as tabelas se não existirem (não apagar dados em reinício)
        db.create_all()
    app.run(debug=True)