import os
import re
import time
import requests
import threading
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# URL INTERNA DO RENDER (Copiada do seu log anterior)
uri = "postgresql://db_fazcomfe_user:bo24NlcJANvGehkj97PytDoNyoiT696V@dpg-d6b4mq4hncsc7386sfag-a/db_fazcomfe"
app.config['SQLALCHEMY_DATABASE_URI'] = uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'fazcomfe2026'

db = SQLAlchemy(app)

class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    telefone = db.Column(db.String(20), nullable=False, unique=True)
    pago = db.Column(db.Boolean, default=False)
    valor_base = db.Column(db.Float)

# FUNÇÃO DA PENA (Monitoramento)
def pena_mercado_pago():
    token = "APP_USR-3244228687878580-021915-5528b1d97c9055fab65127d73dc1427d-24221819"
    headers = {"Authorization": f"Bearer {token}"}
    url = "https://api.mercadopago.com/v1/payments/search?sort=date_created&criteria=desc"
    
    while True:
        try:
            with app.app_context():
                r = requests.get(url, headers=headers).json()
                for p in r.get('results', []):
                    if p['status'] == 'approved':
                        valor = p['transaction_amount']
                        id_c = int(round((valor - int(valor)) * 100))
                        cliente = Cliente.query.get(id_c)
                        if cliente and not cliente.pago:
                            cliente.pago = True
                            db.session.commit()
        except: pass
        time.sleep(20)

# Só inicia a pena se não estiver em modo de debug para não travar
if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
    threading.Thread(target=pena_mercado_pago, daemon=True).start()

@app.route('/')
def index():
    total = Cliente.query.count()
    preco = 45.0 if total < 75 else (55.0 if total < 150 else 60.0)
    return render_template('index.html', preco=preco)

@app.route('/reservar', methods=['POST'])
def reservar():
    nome = request.form.get('nome', '').upper()
    tel = re.sub(r"\D", "", request.form.get('telefone', ''))
    preco = 45.0 # Lógica simplificada para teste
    try:
        novo = Cliente(nome=nome, telefone=tel, valor_base=preco)
        db.session.add(novo)
        db.session.commit()
        return redirect(url_for('pagamento', id=novo.id))
    except:
        return "Erro: Telefone já cadastrado."

@app.route('/pagamento/<int:id>')
def pagamento(id):
    c = Cliente.query.get_or_404(id)
    valor_pix = c.valor_base + (c.id / 100.0)
    return f"""
    <div style="text-align:center; background:#000; color:#fff; padding:50px; font-family:sans-serif;">
        <h2>PAGAMENTO PIX</h2>
        <h1 style="color:#2ecc71">R$ {valor_pix:.2f}</h1>
        <p>Chave: 21 97595-4118</p>
        <a href="/ingresso/{id}" style="color:#f1c40f;">VER MEU INGRESSO</a>
    </div>
    """

@app.route('/ingresso/<int:id>')
def ingresso(id):
    c = Cliente.query.get_or_404(id)
    if not c.pago: return "<h1>Aguardando pagamento...</h1>"
    return render_template('obrigado.html', nome=c.nome)

if __name__ == '__main__':
    with app.app_context(): db.create_all()
    app.run()