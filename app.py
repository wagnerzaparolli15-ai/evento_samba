import os, re, time, requests, threading
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# CONEXÃO INTERNA (Rápida e direta no Render)
app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://db_fazcomfe_user:bo24NlcJANvGehkj97PytDoNyoiT696V@dpg-d6b4mq4hncsc7386sfag-a/db_fazcomfe"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'fazcomfe2026'

db = SQLAlchemy(app)

# Modelo do Banco de Dados
class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    telefone = db.Column(db.String(20), nullable=False, unique=True)
    pago = db.Column(db.Boolean, default=False)
    valor_base = db.Column(db.Float)

# INTEGRAÇÃO MERCADO PAGO (Monitoramento 24h)
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
                        # Identifica o cliente pelos centavos (Ex: 45.15 -> ID 15)
                        id_c = int(round((v - int(v)) * 100))
                        c = Cliente.query.get(id_c)
                        if c and not c.pago:
                            c.pago = True
                            db.session.commit()
                            print(f"✅ Pagamento confirmado: {c.nome}")
        except: pass
        time.sleep(30)

# Inicia a automação em segundo plano
threading.Thread(target=monitor_mp, daemon=True).start()

# Cria as tabelas se não existirem
with app.app_context():
    db.create_all()

# --- ROTAS ---

@app.route('/')
def index():
    total = Cliente.query.count()
    # Lotes: 45 | 55 | 60
    preco = 45.0 if total < 75 else (55.0 if total < 150 else 60.0)
    return render_template('index.html', preco=preco)

@app.route('/reservar', methods=['POST'])
def reservar():
    nome = request.form.get('nome', '').upper()
    tel = re.sub(r"\D", "", request.form.get('telefone', ''))
    try:
        novo = Cliente(nome=nome, telefone=tel, valor_base=45.0)
        db.session.add(novo)
        db.session.commit()
        return redirect(url_for('pagamento', id=novo.id))
    except:
        db.session.rollback()
        return "Erro: Este telefone já está cadastrado."

@app.route('/pagamento/<int:id>')
def pagamento(id):
    c = Cliente.query.get_or_404(id)
    valor_final = c.valor_base + (c.id / 100.0)
    return f"""
    <div style="text-align:center; background:#000 url('/static/fundo.jpg') no-repeat center; background-size:cover; color:#fff; padding:100px; font-family:sans-serif; min-height:100vh;">
        <div style="background:rgba(0,0,0,0.8); display:inline-block; padding:30px; border:2px solid #f1c40f; border-radius:15px;">
            <img src="/static/logo.png" style="width:150px;"><br>
            <h2 style="color:#f1c40f">PAGAMENTO PIX</h2>
            <p>Pague o valor <b>EXATO</b> abaixo:</p>
            <h1 style="color:#2ecc71">R$ {valor_final:.2f}</h1>
            <p>Chave Celular: <b>21 97595-4118</b></p>
            <p style="color:#e74c3c">⚠️ NÃO ALTERE OS CENTAVOS!</p>
            <a href="/ingresso/{id}" style="background:#f1c40f; color:#000; padding:15px 30px; text-decoration:none; font-weight:bold; border-radius:8px; display:inline-block; margin-top:20px;">JÁ PAGUEI, VER MEU INGRESSO</a>
        </div>
    </div>
    """

@app.route('/ingresso/<int:id>')
def ingresso(id):
    c = Cliente.query.get_or_404(id)
    if not c.pago:
        return "<h1>Aguardando confirmação do PIX...</h1><p>O sistema confere a cada 30 segundos. Atualize a página em breve.</p>"
    # Passa o link de check-in para o QR Code no template obrigado.html
    checkin_url = url_for('checkin', id=c.id, _external=True)
    return render_template('obrigado.html', nome=c.nome, checkin_url=checkin_url)

@app.route('/checkin/<int:id>')
def checkin(id):
    c = Cliente.query.get_or_404(id)
    if c.pago:
        return f"<h1 style='text-align:center; color:green;'>ENTRADA LIBERADA:<br>{c.nome}</h1>"
    return "<h1>PAGAMENTO NÃO ENCONTRADO</h1>"

@app.route('/admin_cara')
def admin():
    clientes_raw = Cliente.query.all()
    # Converte para o formato de lista que o seu admin.html já usa
    clientes = [(c.id, c.nome, c.telefone) for c in clientes_raw]
    return render_template('admin.html', clientes=clientes)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)