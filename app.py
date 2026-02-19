import os, re, time, requests, threading
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

app = Flask(__name__)

# CONEXÃO INTERNA BLINDADA
uri = "postgresql://db_fazcomfe_user:bo24NlcJANvGehkj97PytDoNyoiT696V@dpg-d6b4mq4hncsc7386sfag-a/db_fazcomfe?sslmode=require"

app.config['SQLALCHEMY_DATABASE_URI'] = uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'fazcomfe2026'

# RESOLVE O ERRO SSL SYSCALL E EOF DETECTED
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "pool_size": 1,
    "max_overflow": 0,
    "pool_pre_ping": True,
    "pool_recycle": 60,
}

db = SQLAlchemy(app)

# MODELO COMPLETO
class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    telefone = db.Column(db.String(20), nullable=False, unique=True)
    pago = db.Column(db.Boolean, default=False)
    valor_base = db.Column(db.Float)

# A PENA (AUTOMAÇÃO MERCADO PAGO)
def monitor_mp():
    token = "APP_USR-3244228687878580-021915-5528b1d97c9055fab65127d73dc1427d-24221819"
    headers = {"Authorization": f"Bearer {token}"}
    while True:
        try:
            with app.app_context():
                r = requests.get("https://api.mercadopago.com/v1/payments/search?sort=date_created&criteria=desc", headers=headers, timeout=10).json()
                for p in r.get('results', []):
                    if p['status'] == 'approved':
                        v = p['transaction_amount']
                        # Identifica centavos como ID
                        id_c = int(round((v - int(v)) * 100))
                        c = Cliente.query.get(id_c)
                        if c and not c.pago:
                            c.pago = True
                            db.session.commit()
                            print(f"✅ Pagamento confirmado: {c.nome}")
        except: pass
        time.sleep(30)

# --- INICIALIZAÇÃO COM RESET FORÇADO (PARA CORRIGIR ERROS DE COLUNA) ---
with app.app_context():
    try:
        # COMANDO DE LIMPEZA: Remove a tabela antiga com erro e cria a nova
        db.session.execute(text("DROP TABLE IF EXISTS cliente CASCADE"))
        db.session.commit()
        db.create_all()
        print("✅ Banco de dados resetado e atualizado com sucesso!")
    except Exception as e:
        print(f"Aviso no banco: {e}")

# Inicia a automação em segundo plano
threading.Thread(target=monitor_mp, daemon=True).start()

# --- ROTAS ---

@app.route('/')
def index():
    try:
        total = Cliente.query.count()
        preco = 45.0 if total < 75 else (55.0 if total < 150 else 60.0)
        return render_template('index.html', preco=preco)
    except Exception as e:
        return f"O sistema está reiniciando. Atualize a página em 10 segundos."

@app.route('/reservar', methods=['POST'])
def reservar():
    nome = request.form.get('nome', '').upper().strip()
    tel = re.sub(r"\D", "", request.form.get('telefone', ''))
    try:
        total = Cliente.query.count()
        preco_atual = 45.0 if total < 75 else (55