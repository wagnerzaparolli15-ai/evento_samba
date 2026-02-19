# 🥁 Pagode do Cara - Sistema de Ingressos Automático

Este é o sistema oficial do **Pagode do Cara**, projetado para rodar de forma independente no Render, gerindo vendas de ingressos via PIX com confirmação automática através do Mercado Pago.

## 🚀 Como Funciona a Magia (A Pena)
O sistema utiliza uma lógica de identificação por centavos:
1. O cliente faz a reserva (R$ 45,00).
2. O sistema gera um valor único usando o ID do cliente nos centavos (Ex: Cliente #15 paga **R$ 45,15**).
3. A "Pena" (script de monitorização) varre o seu Mercado Pago a cada 30 segundos.
4. Quando encontra um pagamento de R$ 45,15, ela sabe que é do Cliente #15 e liberta o ingresso automaticamente.

## 🛠️ Tecnologias Utilizadas
- **Backend:** Flask (Python)
- **Banco de Dados:** PostgreSQL (Render)
- **Servidor Web:** Gunicorn
- **Integração:** API do Mercado Pago

## 📦 Estrutura de Ficheiros
- `app.py`: O cérebro do sistema e a automação.
- `static/`: Onde devem estar a sua `logo.png` e `fundo.jpg`.
- `templates/`: As páginas visuais (`index`, `pagamento`, `obrigado`, `admin`).

## ⚙️ Configuração no Render (Settings)
Para o sistema funcionar sem erros de SSL ou de porta, use estas configurações no painel do Render:
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `gunicorn app:app --workers 1 --threads 1 --bind 0.0.0.0:10000`
- **Environment Variables:**
  - `PORT`: 10000
  - `PYTHON_VERSION`: 3.14 (ou a versão que estiver a usar)

## 📊 Painel de Administração
Pode conferir a lista de quem já pagou em:
`https://evento-samba.onrender.com/admin_cara`

---
*Faz com Fé Produções - 2026*