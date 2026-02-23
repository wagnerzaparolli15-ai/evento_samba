import os, re, mercadopago
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

app = Flask(__name__, static_folder='static', static_url_path='/static')

# --- BANCO DE DADOS ---
uri = "postgresql://db_fazcomfe_user:bo24NlcJANvGehkj97PytDoNyoiT696V@dpg-d6b4mq4hncsc7386sfag-a/db_fazcomfe?sslmode=require"
app.config['SQLALCHEMY_DATABASE_URI'] = uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- MERCADO PAGO ---
sdk = mercadopago.SDK("APP_USR-3244228687878580-021915-5528b1d97c9055fab65127d73dc1427d-24221819")

class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100))
    telefone = db.Column(db.String(20), unique=True)
    pago = db.Column(db.Boolean, default=False)
    utilizado = db.Column(db.Boolean, default=False)
    payment_id = db.Column(db.String(100)) # SALVA O ID DO PIX AQUI

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('index.html', preco=45.0)

@app.route('/reservar', methods=['POST'])
def reservar():
    nome = request.form.get('nome', '').upper().strip()
    tel = re.sub(r"\D", "", request.form.get('telefone', ''))
    c = Cliente.query.filter_by(telefone=tel).first()
    if not c:
        c = Cliente(nome=nome, telefone=tel)
        db.session.add(c)
        db.session.commit()
    return redirect(url_for('pagamento', id=c.id))

@app.route('/pagamento/<int:id>')
def pagamento(id):
    c = Cliente.query.get_or_404(id)
    pay_data = {
        "transaction_amount": 45.00,
        "description": f"Ingresso Bafafá - {c.nome}",
        "payment_method_id": "pix",
        "payer": {"email": "wagnerzaparolli15@gmail.com"}
    }
    result = sdk.payment().create(pay_data)
    pix = result["response"]["point_of_interaction"]["transaction_data"]
    
    # SALVA O ID DO PAGAMENTO PARA CONSULTAR DEPOIS
    c.payment_id = str(result["response"]["id"])
    db.session.commit()
    
    return render_template('pagamento.html', c=c, pix_codigo=pix["qr_code"], qrcode_base64=pix["qr_code_base64"])

# ROTA QUE O MERCADO PAGO CHAMA PARA AVISAR QUE PAGOU
@app.route('/notificar', methods=['POST'])
def notificar():
    payment_id = request.args.get('data.id') or request.json.get('data', {}).get('id')
    if payment_id:
        info = sdk.payment().get(payment_id)
        if info["response"]["status"] == "approved":
            c = Cliente.query.filter_by(payment_id=str(payment_id)).first()
            if c:
                c.pago = True
                db.session.commit()
    return "OK", 200

@app.route('/ingresso/<int:id>')
def validar_ingresso(id):
    c = Cliente.query.get_or_404(id)
    
    # VERIFICAÇÃO ATIVA: Pergunta ao Mercado Pago antes de abrir
    if not c.pago and c.payment_id:
        info = sdk.payment().get(c.payment_id)
        if info["response"]["status"] == "approved":
            c.pago = True
            db.session.commit()
        else:
            # Se não pagou, ele manda para uma tela de espera
            return render_template('templates-feedback.html', tipo='aguardando')
    
    checkin_url = f"https://evento-samba.onrender.com/checkin/{c.id}"
    return render_template('obrigado.html', nome=c.nome, id_reserva=c.id, checkin_url=checkin_url)

@app.route('/checkin/<int:id>')
def checkin(id):
    c = Cliente.query.get_or_404(id)
    c.utilizado = True
    c.pago = True
    db.session.commit()
    return render_template('recepcao.html', c=c)

@app.route('/admin/reset-total')
def reset_total():
    db.session.execute(text("DROP TABLE IF EXISTS bar_produtos CASCADE;"))
    db.session.execute(text("DROP TABLE IF EXISTS cliente CASCADE;"))
    db.session.commit()
    db.create_all()
    return "<h1>Sucesso! Sistema limpo.</h1><a href='/'>Voltar</a>"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)