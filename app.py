import os
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# CONFIGURAÇÃO DE CONEXÃO
uri = os.environ.get('DATABASE_URL')
if uri and uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)

if uri and "sslmode" not in uri and "localhost" not in uri:
    separator = "&" if "?" in uri else "?"
    uri += f"{separator}sslmode=require"

app.config['SQLALCHEMY_DATABASE_URI'] = uri or 'sqlite:///projeto.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# MODELO DE CLIENTE
class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    telefone = db.Column(db.String(20), nullable=False)
    valor_pago = db.Column(db.Float)
    lote = db.Column(db.Integer)
    compareceu = db.Column(db.Boolean, default=False)

@app.route('/')
def index():
    # Verifica quantos ingressos já foram vendidos
    total_vendido = Cliente.query.count()
    if total_vendido >= 150:
        return "<h1>Ingressos Esgotados!</h1>"
    
    # Define o preço e lote atual para exibir na home
    preco_atual = 45.0 if total_vendido < 75 else 55.0
    lote_atual = 1 if total_vendido < 75 else 2
    
    return render_template('index.html', preco=preco_atual, lote=lote_atual)

@app.route('/comprar', methods=['POST'])
def comprar():
    nome = request.form.get('nome')
    telefone = request.form.get('telefone')
    
    total_vendido = Cliente.query.count()
    
    if total_vendido < 75:
        valor = 45.0
        lote = 1
    elif total_vendido < 150:
        valor = 55.0
        lote = 2
    else:
        return "<h1>Esgotado!</h1>"

    if nome and telefone:
        novo_cliente = Cliente(nome=nome, telefone=telefone, valor_pago=valor, lote=lote)
        db.session.add(novo_cliente)
        db.session.commit()
        return render_template('obrigado.html', nome=nome, id_cliente=novo_cliente.id, valor=valor)
    return redirect(url_for('index'))

@app.route('/checkin/<int:id>')
def checkin(id):
    cliente = Cliente.query.get_or_404(id)
    if cliente.compareceu:
        return f"<div style='text-align:center;padding:50px;'><h1 style='color:orange'>ALERTA: {cliente.nome} JÁ ENTROU!</h1></div>"
    cliente.compareceu = True
    db.session.commit()
    return f"<div style='text-align:center;padding:50px;'><h1 style='color:green'>ENTRADA LIBERADA: {cliente.nome}</h1></div>"

@app.route('/admin-cara-2026')
def admin():
    clientes = Cliente.query.all()
    total_inscritos = len(clientes)
    total_presentes = len([c for c in clientes if c.compareceu])
    faturamento_total = sum([c.valor_pago for c in clientes])
    
    return render_template('admin.html', 
                           clientes=clientes, 
                           total=total_inscritos, 
                           presentes=total_presentes, 
                           faturamento=faturamento_total)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)