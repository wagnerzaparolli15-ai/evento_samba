import os
import re
import time
import requests
import threading
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# CONFIGURAÇÃO DO BANCO (Usando sua Internal URL do Render)
uri = "postgresql://db_fazcomfe_user:bo24NlcJANvGehkj97PytDoNyoiT696V@dpg-d6b4mq4hncsc7386sfag-a/db_fazcomfe"
app.config['SQLALCHEMY_DATABASE_URI'] = uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'fazcomfe-prod-2026'

db = SQLAlchemy(app)

class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    telefone = db.Column(db.String(20), nullable=False, unique=True)
    pago = db.Column(db.Boolean, default=False)
    valor_base = db.Column(db.Float)

# ---------------------------------------------------------
# A "PENA" INTEGRADA (Monitoramento 24h no Render)
# ---------------------------------------------------------
def monitoramento_mercado_pago():
    token = "APP_USR-3244228687878580-021915-5528b1d97c9055fab65127d73dc1427d-24221819"
    headers = {"Authorization": f"Bearer {token}"}
    url = "https://api.mercadopago.com/v1/payments/search?sort=date_created&criteria=desc"

    while True:
        try:
            with app.app_context():
                response = requests.get(url, headers=headers).json()
                for p in response.get('results', []):
                    if p['status'] == 'approved':
                        valor = p['transaction_amount']
                        # Identifica ID pelos centavos (Ex: 45.12 -> ID 12)
                        id_cliente = int(round((valor - int(valor)) * 100))
                        
                        cliente = Cliente.query.get(id_cliente)
                        if cliente and not cliente.pago:
                            cliente.pago = True
                            db.session.commit()
                            print(f"✅ Ingresso #{id_cliente} liberado automaticamente!")
        except Exception as e:
            print(f"Erro no monitoramento: {e}")
        time.sleep(30)

threading.Thread(target=monitoramento_mercado_pago, daemon=True).start()

# ---------------------------------------------------------
# ROTAS
# ---------------------------------------------------------
@app.route('/')
def index():
    total = Cliente.query.count()
    if total >= 300: return "<h1>Lotes Esgotados!</h1>"
    # Lotes: 75(45) | 75(55) | 150(60)
    preco = 45.0 if total < 75 else (55.0 if total < 150 else 60.0)
    return render_template('index.html', preco=preco)

@app.route('/reservar', methods=['POST'])
def reservar():
    nome = request.form.get('nome', '').strip().upper()
    tel = re.sub(r"\D", "", request.form.get('telefone', ''))
    total = Cliente.query.count()
    preco = 45.0 if total < 75 else (55.0 if total < 150 else 60.0)
    try:
        novo = Cliente(nome=nome, telefone=tel, valor_base=preco)
        db.session.add(novo)
        db.session.commit()
        return redirect(url_for('pagamento', id=novo.id))
    except:
        db.session.rollback()
        return "Telefone já cadastrado!"

@app.route('/pagamento/<int:id>')
def pagamento(id):
    c = Cliente.query.get_or_404(id)
    valor_pix = c.valor_base + (c.id / 100.0)
    # Aqui vamos usar o index.html de novo, mas com a instrução do PIX
    return render_template('pagamento.html', c=c, valor_pix=valor_pix)

@app.route('/ingresso/<int:id>')
def ingresso(id):
    c = Cliente.query.get_or_404(id)
    if not c.pago:
        return "<h1>Aguardando PIX...</h1><p>Assim que pagar, atualize esta página.</p>"
    checkin_url = url_for('checkin', id=c.id, _external=True)
    return render_template('obrigado.html', nome=c.nome, checkin_url=checkin_url)

@app.route('/checkin/<int:id>')
def checkin(id):
    c = Cliente.query.get_or_404(id)
    return f"<h1>LIBERADO: {c.nome}</h1>" if c.pago else "<h1>PENDENTE</h1>"

@app.route('/admin_cara')
def admin():
    clientes = Cliente.query.all()
    return render_template('admin.html', clientes=[(c.id, c.nome, c.telefone) for c in clientes])

if __name__ == '__main__':
    with app.app_context(): db.create_all()
    app.run(debug=True)