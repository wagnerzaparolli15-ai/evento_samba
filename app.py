import os
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# CONFIGURAÇÃO DE CONEXÃO OTIMIZADA
uri = os.environ.get('DATABASE_URL')
if uri and uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)

if uri and "sslmode" not in uri and "localhost" not in uri:
    separator = "&" if "?" in uri else "?"
    uri += f"{separator}sslmode=require"

app.config['SQLALCHEMY_DATABASE_URI'] = uri or 'sqlite:///projeto.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# MODELO COMPLETO: ID, NOME, WHATSAPP, VALOR, LOTE E PRESENÇA
class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    telefone = db.Column(db.String(20), nullable=False)
    valor_pago = db.Column(db.Float)
    lote = db.Column(db.Integer)
    compareceu = db.Column(db.Boolean, default=False)

@app.route('/')
def index():
    total_vendido = Cliente.query.count()
    if total_vendido >= 150:
        return "<h1 style='text-align:center;padding-top:50px;'>INGRESSOS ESGOTADOS!</h1>"
    
    # Lógica de Preço: 1º Lote (75 un) R$ 45 | 2º Lote (75 un) R$ 55
    preco_atual = 45.0 if total_vendido < 75 else 55.0
    lote_atual = 1 if total_vendido < 75 else 2
    
    return render_template('index.html', preco=preco_atual, lote=lote_atual)

@app.route('/comprar', methods=['POST'])
def comprar():
    nome = request.form.get('nome').upper()
    telefone = request.form.get('telefone')
    total_vendido = Cliente.query.count()
    
    if total_vendido < 75:
        valor, lote = 45.0, 1
    elif total_vendido < 150:
        valor, lote = 55.0, 2
    else:
        return "Esgotado!"

    if nome and telefone:
        novo = Cliente(nome=nome, telefone=telefone, valor_pago=valor, lote=lote)
        db.session.add(novo)
        db.session.commit()
        return render_template('obrigado.html', nome=nome, id_cliente=novo.id, valor=valor)
    return redirect(url_for('index'))

@app.route('/checkin/<int:id>')
def checkin(id):
    cliente = Cliente.query.get_or_404(id)
    if cliente.compareceu:
        msg, cor = f"ALERTA: {cliente.nome} JÁ ENTROU!", "orange"
    else:
        cliente.compareceu = True
        db.session.commit()
        msg, cor = f"LIBERADO: {cliente.nome}!", "green"
    return f"<div style='text-align:center;padding:50px;font-family:sans-serif;'><h1 style='color:{cor}'>{msg}</h1><a href='/admin-cara-2026'>Voltar</a></div>"

@app.route('/admin-cara-2026')
def admin():
    clientes = Cliente.query.order_by(Cliente.id.desc()).all()
    faturamento = sum([c.valor_pago for c in clientes])
    presentes = len([c for c in clientes if c.compareceu])
    return render_template('admin.html', clientes=clientes, total=len(clientes), faturamento=faturamento, presentes=presentes)

if __name__ == '__main__':
    with app.app_context():
        # ATENÇÃO: Descomente as duas linhas abaixo APENAS SE der Erro 500 de novo para resetar o banco
        # db.drop_all() 
        db.create_all()
    app.run(debug=True)