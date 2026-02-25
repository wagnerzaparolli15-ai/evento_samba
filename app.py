import os, mercadopago, qrcode, io, base64
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func

app = Flask(__name__)

# --- INFRAESTRUTURA ---
db_url = os.getenv("DATABASE_URL")
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url or "sqlite:///bafafa_2026.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.getenv("SECRET_KEY", "BAFAFA_CORP_2026_TOTAL")

db = SQLAlchemy(app)
sdk = mercadopago.SDK(os.getenv("MP_ACCESS_TOKEN"))

# --- MODELOS ---
class Equipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100)); usuario = db.Column(db.String(50), unique=True)
    senha = db.Column(db.String(50)); cargo = db.Column(db.String(30)); cachet = db.Column(db.Float, default=0.0)

class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True); nome = db.Column(db.String(100)); telefone = db.Column(db.String(20))
    pago = db.Column(db.Boolean, default=False); na_casa = db.Column(db.Boolean, default=False)
    metodo = db.Column(db.String(20), default="pix"); valor_total = db.Column(db.Float, default=45.0)

class Produto(db.Model):
    id = db.Column(db.Integer, primary_key=True); nome = db.Column(db.String(100))
    preco_venda = db.Column(db.Float, default=0.0); estoque = db.Column(db.Integer, default=0)

class PedidoBar(db.Model):
    id = db.Column(db.Integer, primary_key=True); cliente_id = db.Column(db.Integer)
    produto_nome = db.Column(db.String(100)); pago = db.Column(db.Boolean, default=False)
    entregue = db.Column(db.Boolean, default=False)

class CustoOperacional(db.Model):
    id = db.Column(db.Integer, primary_key=True); descricao = db.Column(db.String(100)); valor = db.Column(db.Float)

# --- FUNÇÃO AUXILIAR: GERADOR DE QR CODE INTERNO ---
def gerar_qr_interno(link):
    qr = qrcode.make(link)
    buf = io.BytesIO()
    qr.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()

# --- FLUXO DE PAGAMENTO (MERCADO PAGO) ---
@app.route('/pagamento/<int:id>')
def pagamento(id):
    c = Cliente.query.get_or_404(id)
    if c.pago: return redirect(url_for('ingresso', id=c.id))
    try:
        pay_data = {"transaction_amount": 45.0, "description": "Ingresso Bafafá", "payment_method_id": "pix", "payer": {"email": "vendas@bafafa.com"}}
        res = sdk.payment().create(pay_data)
        qr_pix = res["response"]["point_of_interaction"]["transaction_data"]["qr_code"]
        # Gera o QR Code da biblioteca usando o link que o Mercado Pago mandou
        return render_template('pagamento.html', c=c, qr_img=gerar_qr_interno(qr_pix), pix_copia_cola=qr_pix, tipo='pix')
    except:
        return render_template('templates-feedback.html', tipo='erro', msg="Erro no PIX. Use aprovação manual no Admin.")

# --- FLUXO DE INGRESSO (CHECK-IN INTERNO) ---
@app.route('/ingresso/<int:id>')
def ingresso(id):
    c = Cliente.query.get_or_404(id)
    if not c.pago: return render_template('templates-feedback.html', tipo='aguardando', c=c)
    
    # Link que a Liza vai abrir ao escanear
    link_checkin = f"https://evento-samba.onrender.com/validar-entrada/{c.id}"
    qr_checkin = gerar_qr_interno(link_checkin)
    
    return render_template('obrigado.html', c=c, qr_checkin=qr_checkin)

# --- VALIDAÇÕES STAFF (O CORAÇÃO DO FLUXO) ---
@app.route('/validar-entrada/<int:id>')
def validar_entrada(id):
    if session.get('cargo') not in ['admin', 'portaria']: return redirect(url_for('login_staff'))
    c = Cliente.query.get_or_404(id)
    c.na_casa = True
    db.session.commit()
    # Retorna uma confirmação visual para a Liza
    return f"<body style='background:#000;color:#0f8;text-align:center;padding-top:50px;font-family:sans-serif;'><h1>✅ ENTRADA LIBERADA: {c.nome}</h1><br><a href='/portaria' style='color:#fff;'>Voltar para Lista</a></body>"

@app.route('/entregar-bebida/<int:id>')
def entregar_bebida(id):
    if session.get('cargo') not in ['admin', 'bar']: return redirect(url_for('login_staff'))
    p = PedidoBar.query.get_or_404(id)
    p.entregue = True
    db.session.commit()
    return f"<body style='background:#000;color:#0f8;text-align:center;padding-top:50px;font-family:sans-serif;'><h1>✅ BEBIDA ENTREGUE: {p.produto_nome}</h1><br><a href='/login-staff' style='color:#fff;'>Voltar</a></body>"

# --- ADMIN E MANUTENÇÃO ---
@app.route('/admin_total', methods=['GET', 'POST'])
def admin_total():
    if session.get('cargo') not in ['admin', 'gerente']: return redirect(url_for('login_staff'))
    if request.method == 'POST':
        tipo = request.form.get('form_tipo')
        if tipo == 'equipe':
            db.session.add(Equipe(nome=request.form.get('n'), usuario=request.form.get('u'), senha=request.form.get('s'), cargo=request.form.get('c')))
        db.session.commit()
    
    entradas = db.session.query(func.sum(Cliente.valor_total)).filter(Cliente.pago==True).scalar() or 0
    custos = db.session.query(func.sum(CustoOperacional.valor)).scalar() or 0
    return render_template('admin_total.html', total_entradas=entradas, total_custos=custos, 
                           equipe=Equipe.query.all(), clientes_pendentes=Cliente.query.filter_by(pago=False).all())

@app.route('/aprovar-manual/<int:id>')
def aprovar_manual(id):
    if session.get('cargo') not in ['admin', 'gerente']: return redirect(url_for('login_staff'))
    c = Cliente.query.get_or_404(id); c.pago = True; db.session.commit()
    return redirect(url_for('admin_total'))

@app.route('/login-staff', methods=['GET', 'POST'])
def login_staff():
    if request.method == 'POST':
        u = Equipe.query.filter_by(usuario=request.form.get('username'), senha=request.form.get('senha')).first()
        if u:
            session.update({'cargo': u.cargo, 'usuario_nome': u.nome})
            return redirect(url_for('admin_total' if u.cargo in ['admin', 'gerente'] else 'portaria'))
    return render_template('login_staff.html')

@app.route('/reset-bruto-bafafa')
def reset():
    db.drop_all(); db.create_all()
    db.session.add(Equipe(nome='Wagner Master', usuario='wagner', senha='123', cargo='admin'))
    db.session.commit()
    return "✅ SISTEMA RESETADO E PRONTO!"

if __name__ == '__main__':
    with app.app_context(): db.create_all()
    app.run(host='0.0.0.0', port=10000)