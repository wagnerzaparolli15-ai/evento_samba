import os, re, time, requests, threading
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text  # IMPORTANTE: Adicionado para o comando SQL

app = Flask(__name__)
uri = "postgresql://db_fazcomfe_user:bo24NlcJANvGehkj97PytDoNyoiT696V@dpg-d6b4mq4hncsc7386sfag-a/db_fazcomfe?sslmode=require"
app.config['SQLALCHEMY_DATABASE_URI'] = uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    telefone = db.Column(db.String(20), nullable=False, unique=True)
    pago = db.Column(db.Boolean, default=False)
    utilizado = db.Column(db.Boolean, default=False) 
    valor_base = db.Column(db.Float)

# --- CORREÇÃO AUTOMÁTICA DO BANCO ---
with app.app_context():
    db.create_all() # Cria tabelas se não existirem
    try:
        # Tenta adicionar a coluna 'utilizado' caso a tabela já exista sem ela
        db.session.execute(text("ALTER TABLE cliente ADD COLUMN utilizado BOOLEAN DEFAULT FALSE;"))
        db.session.commit()
    except Exception:
        db.session.rollback() # Ignora erro se a coluna já existir

# MONITORAMENTO (A PENA)
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
        except: pass
        time.sleep(30)

threading.Thread(target=monitor_mp, daemon=True).start()

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
        return "Erro: Telefone ja cadastrado."

@app.route('/pagamento/<int:id>')
def pagamento(id):
    c = Cliente.query.get_or_404(id)
    valor_pix = c.valor_base + (c.id / 100.0)
    chave_aleatoria = "5e751c11-535c-4e47-97d8-3fbb70d87151"
    return render_template('pagamento.html', c=c, valor_pix=valor_pix, chave=chave_aleatoria)

@app.route('/ingresso/<int:id>')
def ingresso(id):
    c = Cliente.query.get_or_404(id)
    if not c.pago:
        return render_template('templates-feedback.html', tipo='aguardando', id=c.id)
    checkin_url = url_for('checkin', id=c.id, _external=True)
    return render_template('obrigado.html', nome=c.nome, checkin_url=checkin_url, id_reserva=c.id)

@app.route('/checkin/<int:id>')
def checkin(id):
    c = Cliente.query.get_or_404(id)
    if not c.pago:
        return "<h1>ERRO: PAGAMENTO NÃO LOCALIZADO</h1>", 403
    if c.utilizado:
        return f"<h1>❌ QR CODE INVÁLIDO!</h1><p>Este ingresso ja foi usado por {c.nome}.</p>", 410
    
    c.utilizado = True
    db.session.commit()
    return f"<h1>✅ ACESSO LIBERADO!</h1><h2>Bem-vindo, {c.nome}!</h2>"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))