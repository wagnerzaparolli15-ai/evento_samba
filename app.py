import os, re, time, requests, threading
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# URL INTERNA COM SSL MODE (Essencial para o Render não dar erro 500)
uri = "postgresql://db_fazcomfe_user:bo24NlcJANvGehkj97PytDoNyoiT696V@dpg-d6b4mq4hncsc7386sfag-a/db_fazcomfe?sslmode=require"

app.config['SQLALCHEMY_DATABASE_URI'] = uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'fazcomfe2026'

# CONFIGURAÇÃO ANTI-TRAVAMENTO (Resolve o erro "decryption failed")
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "pool_size": 1, 
    "max_overflow": 0,
    "pool_pre_ping": True,
    "pool_recycle": 300,
}

db = SQLAlchemy(app)

# Modelo do Banco (Tabela de Clientes)
class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    telefone = db.Column(db.String(20), nullable=False, unique=True)
    pago = db.Column(db.Boolean, default=False)
    valor_base = db.Column(db.Float)

# INTEGRAÇÃO MERCADO PAGO (A PENA)
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
                        # Centavos = ID do cliente (Ex: 45.18 -> ID 18)
                        id_c = int(round((v - int(v)) * 100))
                        c = Cliente.query.get(id_c)
                        if c and not c.pago:
                            c.pago = True
                            db.session.commit()
                            print(f"✅ Pagamento Confirmado: {c.nome}")
        except: pass
        time.sleep(30)

# Inicia a automação em segundo plano
threading.Thread(target=monitor_mp, daemon=True).start()

# Força a criação das tabelas
with app.app_context():
    db.create_all()

# --- ROTAS ---

@app.route('/')
def index():
    try:
        total = Cliente.query.count()
        preco = 45.0 if total < 75 else (55.0 if total < 150 else 60.0)
        return render_template('index.html', preco=preco)
    except:
        return "<h1>Servidor em manutenção...</h1><p>Atualize em instantes.</p>"

@app.route('/reservar', methods=['POST'])
def reservar():
    nome = request.form.get('nome', '').upper().strip()
    tel = re.sub(r"\D", "", request.form.get('telefone', ''))
    try:
        total = Cliente.query.count()
        preco_atual = 45.0 if total < 75 else (55.0 if total < 150 else 60.0)
        novo = Cliente(nome=nome, telefone=tel, valor_base=preco_atual)
        db.session.add(novo)
        db.session.commit()
        return redirect(url_for('pagamento', id=novo.id))
    except:
        db.session.rollback()
        return "Erro: Telefone já cadastrado ou erro de rede."

@app.route('/pagamento/<int:id>')
def pagamento(id):
    c = Cliente.query.get_or_404(id)
    valor_pix = c.valor_base + (c.id / 100.0)
    return f"""
    <div style="text-align:center; background:#000 url('/static/fundo.jpg') no-repeat center; background-size:cover; color:#fff; padding:60px; font-family:sans-serif; min-height:100vh;">
        <div style="background:rgba(0,0,0,0.8); display:inline-block; padding:30px; border:2px solid #f1c40f; border-radius:15px; max-width:400px;">
            <img src="/static/logo.png" style="width:130px;"><br>
            <h2 style="color:#f1c40f">PAGAMENTO PIX</h2>
            <p>Pague o valor exato para liberação imediata:</p>
            <h1 style="color:#2ecc71">R$ {valor_pix:.2f}</h1>
            <p>Chave Celular: <b>21 97595-4118</b></p>
            <p style="color:#e74c3c">⚠️ NÃO MUDE OS CENTAVOS!</p>
            <a href="/ingresso/{id}" style="background:#f1c40f; color:#000; padding:15px 30px; text-decoration:none; font-weight:bold; border-radius:8px; display:inline-block; margin-top:20px;">JÁ PAGUEI, VER MEU INGRESSO</a>
        </div>
    </div>
    """

@app.route('/ingresso/<int:id>')
def ingresso(id):
    c = Cliente.query.get_or_404(id)
    if not c.pago:
        return "<h1>Aguardando PIX...</h1><p>O sistema confere a cada 30s. <a href='javascript:location.reload()'>Clique aqui para atualizar</a>.</p>"
    checkin_url = url_for('checkin', id=c.id, _external=True)
    return render_template('obrigado.html', nome=c.nome, checkin_url=checkin_url)

@app.route('/checkin/<int:id>')
def checkin(id):
    c = Cliente.query.get_or_404(id)
    if c.pago:
        return f"<body style='text-align:center; padding-top:100px;'><h1>✅ LIBERADO</h1><h2>{c.nome}</h2></body>"
    return "<h1>❌ NÃO PAGO</h1>"

@app.route('/admin_cara')
def admin():
    clientes_raw = Cliente.query.all()
    clientes = [(c.id, c.nome, c.telefone, c.pago) for c in clientes_raw]
    return render_template('admin.html', clientes=clientes)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)