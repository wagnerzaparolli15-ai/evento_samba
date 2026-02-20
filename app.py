import os, re, time, requests, threading
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

app = Flask(__name__)

# CONFIGURAÇÃO DE CONEXÃO (Render)
uri = "postgresql://db_fazcomfe_user:bo24NlcJANvGehkj97PytDoNyoiT696V@dpg-d6b4mq4hncsc7386sfag-a/db_fazcomfe?sslmode=require"
app.config['SQLALCHEMY_DATABASE_URI'] = uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'fazcomfe2026'
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {"pool_pre_ping": True, "pool_size": 1, "max_overflow": 0}

db = SQLAlchemy(app)

# MODELO DO BANCO
class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    telefone = db.Column(db.String(20), nullable=False, unique=True)
    pago = db.Column(db.Boolean, default=False)
    valor_base = db.Column(db.Float)

# A PENA (MONITORAMENTO MERCADO PAGO)
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
                        id_c = int(round((v - int(v)) * 100))
                        c = Cliente.query.get(id_c)
                        if c and not c.pago:
                            c.pago = True
                            db.session.commit()
                            print(f"✅ Pagamento confirmado: {c.nome}")
        except: pass
        time.sleep(30)

# INICIALIZAÇÃO (Cria as tabelas automaticamente)
with app.app_context():
    db.create_all()

# Inicia a Pena em segundo plano
threading.Thread(target=monitor_mp, daemon=True).start()

# --- ROTAS CONECTADAS AOS SEUS HTMLS ---

@app.route('/')
def index():
    total = Cliente.query.count()
    preco = 45.0 if total < 75 else (55.0 if total < 150 else 60.0)
    return render_template('index.html', preco=preco)

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
        # Se o telefone já existir, ele avisa e dá opção de voltar
        return "<h1>Erro: Telefone já cadastrado!</h1><p>Você já fez uma reserva. <a href='/'>Voltar para o início</a></p>"

@app.route('/pagamento/<int:id>')
def pagamento(id):
    c = Cliente.query.get_or_404(id)
    valor_pix = c.valor_base + (c.id / 100.0)
    # Envia os dados para o seu pagamento.html
    return render_template('pagamento.html', c=c, valor_pix=valor_pix)

@app.route('/ingresso/<int:id>')
def ingresso(id):
    c = Cliente.query.get_or_404(id)
    if not c.pago:
        return "<h1>Aguardando PIX...</h1><p>O sistema confere a cada 30 segundos.</p>"
    checkin_url = url_for('checkin', id=c.id, _external=True)
    return render_template('obrigado.html', nome=c.nome, checkin_url=checkin_url)

@app.route('/checkin/<int:id>')
def checkin(id):
    c = Cliente.query.get_or_404(id)
    status = "✅ LIBERADO" if c.pago else "❌ NÃO PAGO"
    return f"<div style='text-align:center; padding-top:50px;'><h1>{status}</h1><h2>{c.nome}</h2></div>"

@app.route('/admin_cara')
def admin():
    # Pega os clientes para o seu admin.html
    clientes = Cliente.query.all()
    return render_template('admin.html', clientes=clientes)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)