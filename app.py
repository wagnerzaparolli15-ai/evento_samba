import os, re, time, requests, threading
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# CONEXÃO INTERNA DEFINITIVA (Rápida e Segura)
app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://db_fazcomfe_user:bo24NlcJANvGehkj97PytDoNyoiT696V@dpg-d6b4mq4hncsc7386sfag-a/db_fazcomfe"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'fazcomfe2026'

db = SQLAlchemy(app)

# Modelo da Tabela
class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    telefone = db.Column(db.String(20), nullable=False, unique=True)
    pago = db.Column(db.Boolean, default=False)
    valor_base = db.Column(db.Float)

# A PENA (Monitoramento que corre 24h no Render)
def monitor_mp():
    token = "APP_USR-3244228687878580-021915-5528b1d97c9055fab65127d73dc1427d-24221819"
    headers = {"Authorization": f"Bearer {token}"}
    while True:
        try:
            with app.app_context():
                r = requests.get("https://api.mercadopago.com/v1/payments/search?sort=date_created&criteria=desc", headers=headers).json()
                for p in r.get('results', []):
                    if p['status'] == 'approved':
                        v = p['transaction_amount']
                        # Extrai ID dos centavos (Ex: 45.12 -> ID 12)
                        id_c = int(round((v - int(v)) * 100))
                        c = Cliente.query.get(id_c)
                        if c and not c.pago:
                            c.pago = True
                            db.session.commit()
                            print(f"✅ Pago: {c.nome}")
        except: pass
        time.sleep(30)

# Inicia a Pena antes do site abrir
threading.Thread(target=monitor_mp, daemon=True).start()

# Força a criação das tabelas ao ligar
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    total = Cliente.query.count()
    # Lógica de Lotes: 75 a 45 | 75 a 55 | 150 a 60
    preco = 45.0 if total < 75 else (55.0 if total < 150 else 60.0)
    return render_template('index.html', preco=preco)

@app.route('/reservar', methods=['POST'])
def reservar():
    nome = request.form.get('nome', '').upper()
    tel = re.sub(r"\D", "", request.form.get('telefone', ''))
    try:
        novo = Cliente(nome=nome, telefone=tel, valor_base=45.0) # Inicia no Lote 1
        db.session.add(novo)
        db.session.commit()
        return redirect(url_for('pagamento', id=novo.id))
    except:
        db.session.rollback()
        return "Erro: Este telefone já está registado."

@app.route('/pagamento/<int:id>')
def pagamento(id):
    c = Cliente.query.get_or_404(id)
    valor = c.valor_base + (c.id / 100.0)
    return f"""
    <div style="text-align:center; background:#000; color:#fff; padding:50px; font-family:sans-serif; border:2px solid #f1c40f; border-radius:15px; max-width:400px; margin:50px auto;">
        <h2 style="color:#f1c40f">PAGAMENTO PIX</h2>
        <h1 style="color:#2ecc71">R$ {valor:.2f}</h1>
        <p>Chave Celular: <b>21 97595-4118</b></p>
        <p style="color:red">⚠️ NÃO MUDE OS CENTAVOS!</p>
        <a href="/ingresso/{id}" style="background:#f1c40f; color:#000; padding:15px; text-decoration:none; font-weight:bold; border-radius:8px; display:block; margin-top:20px;">JÁ PAGUEI, VER MEU INGRESSO</a>
    </div> """

@app.route('/ingresso/<int:id>')
def ingresso(id):
    c = Cliente.query.get_or_404(id)
    if not c.pago: return "<h1>Aguardando PIX...</h1><p>O sistema confere a cada 30s.</p>"
    return render_template('obrigado.html', nome=c.nome)

@app.route('/admin_cara')
def admin():
    clientes = Cliente.query.all()
    # Envia para o admin.html no formato que ele espera
    return render_template('admin.html', clientes=[(c.id, c.nome, c.telefone) for c in clientes])

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)