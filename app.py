import os
from flask import Flask, render_template, request, redirect, url_for, Response
from flask_sqlalchemy import SQLAlchemy
from functools import wraps

app = Flask(__name__)

# CONFIGURAÇÃO DE BANCO DE DADOS (Local: SQLite / Nuvem: Postgres)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///meu_evento.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# MODELO DE DADOS PROFISSIONAL
class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    telefone = db.Column(db.String(20), nullable=False)
    pago = db.Column(db.String(20), default='PENDENTE')

# Cria o banco de dados automaticamente ao iniciar
with app.app_context():
    db.create_all()

# SEGURANÇA: Painel Administrativo do Produtor
def check_auth(username, password):
    return username == 'admin' and password == 'samba2026'

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return Response('Acesso Restrito', 401, {'WWW-Authenticate': 'Basic realm="Login"'})
        return f(*args, **kwargs)
    return decorated

# ROTAS DO SISTEMA
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/cadastrar", methods=["POST"])
def cadastrar():
    nome = request.form.get("nome").upper()
    telefone = request.form.get("telefone")
    if nome and telefone:
        novo = Cliente(nome=nome, telefone=telefone)
        db.session.add(novo)
        db.session.commit()
    return render_template("obrigado.html", nome=nome)

@app.route("/admin")
@requires_auth
def admin():
    clientes = Cliente.query.order_by(Cliente.id.desc()).all()
    return render_template("admin.html", clientes=clientes)

@app.route("/confirmar/<int:id>")
@requires_auth
def confirmar(id):
    cliente = Cliente.query.get(id)
    if cliente:
        cliente.pago = 'PAGO'
        db.session.commit()
    return redirect(url_for('admin'))

if __name__ == "__main__":
    app.run(debug=True)