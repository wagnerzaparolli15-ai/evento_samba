import os, re, mercadopago
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Configuração estável para o Render com proteção de conexão
uri = "postgresql://db_fazcomfe_user:bo24NlcJANvGehkj97PytDoNyoiT696V@dpg-d6b4mq4hncsc7386sfag-a/db_fazcomfe?sslmode=require"
app.config['SQLALCHEMY_DATABASE_URI'] = uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {"pool_pre_ping": True, "pool_recycle": 300}

db = SQLAlchemy(app)

# TOKEN OFICIAL: Chave de produção do Mercado Pago
sdk = mercadopago.SDK("APP_USR-3244228687878580-021915-5528b1d97c9055fab65127d73dc1427d-24221819")

class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100))
    telefone = db.Column(db.String(20), unique=True)
    pago = db.Column(db.Boolean, default=False)
    utilizado = db.Column(db.Boolean, default=False)
    mp_id = db.Column(db.String(100))

# ROTA DE EMERGÊNCIA: Use uma única vez para sincronizar as colunas do banco
@app.route('/reset-banco-sistema-cara')
def reset_banco():
    try:
        db.drop_all()
        db.create_all()
        return "<h1>✅ BANCO DE DADOS SINCRONIZADO!</h1><p>A coluna mp_id foi criada. Volte para a Home e faça seu teste.</p>"
    except Exception as e:
        return f"<h1>❌ ERRO AO RESETAR:</h1><p>{str(e)}</p>"

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('index.html', preco=45.0)

@app.route('/reservar', methods=['POST'])
def reservar():
    nome = request.form.get('nome', '').upper().strip()
    tel = re.sub(r"\D", "", request.form.get('telefone', ''))
    if not nome or not tel:
        return "Erro: Nome e telefone são obrigatórios."
    try:
        # Redireciona direto se o cliente já existir (evita erro de duplicidade)
        cliente_existente = Cliente.query.filter_by(telefone=tel).first()
        if cliente_existente:
            return redirect(url_for('pagamento', id=cliente_existente.id))
            
        novo = Cliente(nome=nome, telefone=tel)
        db.session.add(novo)
        db.session.commit()
        return redirect(url_for('pagamento', id=novo.id))
    except Exception as e:
        db.session.rollback()
        return f"Erro no cadastro: {str(e)}"

@app.route('/pagamento/<int:id>')
def pagamento(id):
    c = Cliente.query.get_or_404(id)
    try:
        primeiro_nome = c.nome.split()[0] if c.nome else "Cliente"
        payment_data = {
            "transaction_amount": 45.00,
            "description": f"Ingresso + Feijoada - {c.nome}",
            "payment_method_id": "pix",
            "payer": {
                "email": "caragrossooficial@gmail.com",
                "first_name": primeiro_nome,
                "last_name": "Samba"
            }
        }
        payment_response = sdk.payment().create(payment_data)
        payment = payment_response.get("response")

        if not payment or "point_of_interaction" not in payment:
            return "Erro ao gerar PIX: Verifique sua conta no Mercado Pago."

        pix_codigo = payment['point_of_interaction']['transaction_data']['qr_code']
        qrcode_base64 = payment['point_of_interaction']['transaction_data']['qr_code_base64']
        
        c.mp_id = str(payment['id'])
        db.session.commit()
        return render_template('pagamento.html', c=c, pix_codigo=pix_codigo, qrcode_base64=qrcode_base64)
    except Exception as e:
        return f"Erro de comunicação: {str(e)}"

@app.route('/ingresso/<int:id>')
def ingresso(id):
    c = Cliente.query.get_or_404(id)
    # Validação automática com a API do Mercado Pago
    if not c.pago and c.mp_id:
        try:
            payment_info = sdk.payment().get(c.mp_id)
            if payment_info.get("response", {}).get("status") == "approved":
                c.pago = True
                db.session.commit()
        except:
            pass
    if not c.pago:
        return render_template('templates-feedback.html', tipo='aguardando', id=c.id)
    
    checkin_url = url_for('checkin', id=c.id, _external=True)
    return render_template('obrigado.html', nome=c.nome, checkin_url=checkin_url, id_reserva=c.id)

@app.route('/checkin/<int:id>')
def checkin(id):
    c = Cliente.query.get_or_404(id)
    if not c.pago:
        return "<h1>❌ ERRO: PAGAMENTO NÃO LOCALIZADO</h1>", 403
    if c.utilizado:
        return f"<h1>❌ QR CODE INVÁLIDO!</h1><p>Usado por {c.nome}.</p>", 410
    
    c.utilizado = True
    db.session.commit()
    return f"<h1>✅ ACESSO LIBERADO!</h1><h2>Bem-vindo, {c.nome}!</h2>"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))