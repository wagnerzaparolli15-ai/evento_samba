import os, mercadopago, qrcode, io, base64
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func

app = Flask(__name__)

# --- CONFIGURAÇÃO DE INFRAESTRUTURA ---
db_url = os.getenv("DATABASE_URL")
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url or "sqlite:///bafafa_2026.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.getenv("SECRET_KEY", "BAFAFA_CORP_2026_TOTAL")

db = SQLAlchemy(app)

# Inicializa o SDK com o Token do Render
# Certifique-se que o nome no Render é exatamente MP_ACCESS_TOKEN
sdk = mercadopago.SDK(os.getenv("MP_ACCESS_TOKEN"))

# --- MODELOS DE DADOS ---
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
    imagem = db.Column(db.String(100)); preco_venda = db.Column(db.Float, default=0.0); estoque = db.Column(db.Integer, default=0)

class CustoOperacional(db.Model):
    id = db.Column(db.Integer, primary_key=True); descricao = db.Column(db.String(100)); valor = db.Column(db.Float)

# --- ROTAS DE PAGAMENTO (CORRIGIDAS) ---

@app.route('/')
def index(): return render_template('index.html')

@app.route('/reservar', methods=['POST'])
def reservar():
    nome = request.form.get('nome', '').upper().strip()
    telefone = request.form.get('telefone', '').strip()
    if not nome or not telefone:
        return redirect(url_for('index'))
    c = Cliente(nome=nome, telefone=telefone)
    db.session.add(c); db.session.commit()
    return redirect(url_for('pagamento', id=c.id))

@app.route('/pagamento/<int:id>')
def pagamento(id):
    c = Cliente.query.get_or_404(id)
    if c.pago: return redirect(url_for('ingresso', id=c.id))
    
    try:
        # Montagem do pagamento PIX
        payment_data = {
            "transaction_amount": 45.0,
            "description": f"Ingresso Bafafá 2026 - {c.nome}",
            "payment_method_id": "pix",
            "payer": {
                "email": "pagamento@bafafa2026.com", # E-mail genérico para evitar conflitos
                "first_name": c.nome.split()[0],
                "last_name": "Cliente"
            }
        }
        
        res = sdk.payment().create(payment_data)
        
        # Se o Mercado Pago responder com sucesso (Status 201)
        if res["status"] == 201:
            qr_pix = res["response"]["point_of_interaction"]["transaction_data"]["qr_code"]
            img = qrcode.make(qr_pix)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            qr_b64 = base64.b64encode(buf.getvalue()).decode()
            
            return render_template('pagamento.html', c=c, qr_img=qr_b64, pix_copia_cola=qr_pix, tipo='pix')
        else:
            print(f"Erro Mercado Pago: {res['response']}")
            raise Exception("Resposta inválida do MP")

    except Exception as e:
        print(f"ERRO CRÍTICO NO PAGAMENTO: {e}")
        # Se falhar, manda para a página de aviso que já temos
        return render_template('templates-feedback.html', tipo='erro', msg="O sistema de PIX está instável. Mostre este ecrã na portaria para pagar lá.")

# --- DEMAIS ROTAS (GESTÃO E RESET) ---

@app.route('/admin_total', methods=['GET', 'POST'])
def admin_total():
    if session.get('cargo') not in ['admin', 'gerente']: return redirect(url_for('login_staff'))
    # Cálculos de faturamento e custos...
    entradas = db.session.query(func.sum(Cliente.valor_total)).filter(Cliente.pago==True).scalar() or 0
    saidas = (db.session.query(func.sum(CustoOperacional.valor)).scalar() or 0)
    return render_template('admin_total.html', total_entradas=entradas, total_custos=saidas, 
                           produtos=Produto.query.all(), equipe=Equipe.query.all(),
                           clientes_pendentes=Cliente.query.filter_by(pago=False).all())

@app.route('/aprovar-manual/<int:id>')
def aprovar_manual(id):
    if session.get('cargo') not in ['admin', 'gerente']: return "Acesso Negado"
    c = Cliente.query.get_or_404(id)
    c.pago = True; db.session.commit()
    return redirect(url_for('admin_total'))

@app.route('/reset-bruto-bafafa')
def reset():
    try:
        db.drop_all(); db.create_all()
        db.session.add(Equipe(nome='Wagner Master', usuario='wagner', senha='123', cargo='admin'))
        db.session.commit()
        return "✅ SUCESSO! <a href='/login-staff'>Login Admin</a>"
    except Exception as e: return f"Erro: {str(e)}"

# Restante das rotas (login, portaria, ingresso, etc)...
@app.route('/login-staff', methods=['GET', 'POST'])
def login_staff():
    if request.method == 'POST':
        u = Equipe.query.filter_by(usuario=request.form.get('username'), senha=request.form.get('senha')).first()
        if u:
            session.update({'cargo': u.cargo, 'usuario_nome': u.nome})
            return redirect(url_for('admin_total' if u.cargo in ['admin', 'gerente'] else 'portaria'))
    return render_template('login_staff.html')

@app.route('/ingresso/<int:id>')
def ingresso(id):
    c = Cliente.query.get_or_404(id)
    if not c.pago: return render_template('templates-feedback.html', tipo='aguardando', c=c)
    return render_template('obrigado.html', c=c)

if __name__ == '__main__':
    with app.app_context(): db.create_all()
    app.run(host='0.0.0.0', port=10000)