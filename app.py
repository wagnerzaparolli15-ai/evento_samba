import os
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# CONFIGURAÇÃO DE CONEXÃO
uri = os.environ.get('DATABASE_URL')
if uri and uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)
if uri and "sslmode" not in uri:
    uri += "&sslmode=require" if "?" in uri else "?sslmode=require"

app.config['SQLALCHEMY_DATABASE_URI'] = uri or 'sqlite:///fazcomfe.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# MODELO DE DADOS
class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    telefone = db.Column(db.String(20), nullable=False)
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
    nome = request.form.get('nome', '').upper()
    tel = request.form.get('telefone', '')
    try:
        total = Cliente.query.count()
        valor, num_lote = (45.0, 1) if total < 75 else (55.0, 2)
        if nome and tel:
            novo = Cliente(nome=nome, telefone=tel, valor_pago=valor, lote=num_lote)
            db.session.add(novo)
            db.session.commit()
            return render_template('obrigado.html', nome=nome, id_cliente=novo.id, valor=valor)
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
        msg = f"LIBERADO: {c.nome}"
    else:
        msg = f"ALERTA: {c.nome} JÁ ENTROU!"
    return f"<div style='text-align:center;padding:50px;font-family:sans-serif;'><h1>{msg}</h1><a href='/'>Voltar</a></div>"

# INICIALIZAÇÃO COM RESET (DROP_ALL)
if __name__ == '__main__':
    with app.app_context():
        db.drop_all() # APAGA TUDO PARA CRIAR DO ZERO SEM ERRO DE COLUNA
        db.create_all() # CRIA AS TABELAS CERTAS
    app.run(debug=False)