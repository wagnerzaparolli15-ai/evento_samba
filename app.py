import os
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# --- CONFIGURAÇÃO DO BANCO DE DATOS (LIMPA) ---
# Otimiza a URL do banco para o padrão exigido pelo SQLAlchemy e Render
uri = os.environ.get('DATABASE_URL')
if uri and uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)

# Força a conexão segura (SSL) para evitar erros no Render
if uri and "sslmode" not in uri:
    separator = "&" if "?" in uri else "?"
    uri += f"{separator}sslmode=require"

app.config['SQLALCHEMY_DATABASE_URI'] = uri or 'sqlite:///fazcomfe.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- MODELO DE DADOS ---
class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    telefone = db.Column(db.String(20), nullable=False)
    valor_pago = db.Column(db.Float)
    lote = db.Column(db.Integer)
    compareceu = db.Column(db.Boolean, default=False)

# --- ROTAS DO SISTEMA ---

@app.route('/')
def index():
    """Página de vendas com lógica de lotes automática"""
    try:
        total_vendido = Cliente.query.count()
        preco = 45.0 if total_vendido < 75 else 55.0
        lote = 1 if total_vendido < 75 else 2
        return render_template('index.html', preco=preco, lote=lote)
    except:
        return "Erro ao conectar ao banco. Verifique a DATABASE_URL no Render."

@app.route('/comprar', methods=['POST'])
def comprar():
    """Processa a reserva e gera o ingresso"""
    nome = request.form.get('nome', '').upper()
    tel = request.form.get('telefone', '')
    
    total = Cliente.query.count()
    valor, num_lote = (45.0, 1) if total < 75 else (55.0, 2)

    if nome and tel:
        novo = Cliente(nome=nome, telefone=tel, valor_pago=valor, lote=num_lote)
        db.session.add(novo)
        db.session.commit()
        return render_template('obrigado.html', nome=nome, id_cliente=novo.id, valor=valor)
    return redirect(url_for('index'))

@app.route('/checkin/<int:id>')
def checkin(id):
    """Validação de QR Code na Portaria"""
    c = Cliente.query.get_or_404(id)
    if not c.compareceu:
        c.compareceu = True
        db.session.commit()
        msg = f"LIBERADO: {c.nome}"
    else:
        msg = f"ALERTA: {c.nome} JÁ ENTROU!"
    return f"<h1>{msg}</h1><br><a href='/'>Voltar</a>"

@app.route('/admin-cara-2026')
def admin():
    """Painel de Gestão e Faturamento"""
    clientes = Cliente.query.all()
    faturamento = sum([c.valor_pago for c in clientes])
    presentes = len([c for c in clientes if c.compareceu])
    return render_template('admin.html', clientes=clientes, total=len(clientes), faturamento=faturamento, presentes=presentes)

# --- INICIALIZAÇÃO ---
if __name__ == '__main__':
    with app.app_context():
        # Cria as tabelas se elas não existirem
        db.create_all()
    app.run(debug=True)