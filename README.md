# Sistema de Gestão Bafafá 🎷

Sistema completo para venda de ingressos via Pix, controle de portaria e gestão de bar para eventos.

---

## 🚀 Funcionalidades Principais

- ✅ Venda de ingressos com integração ao Mercado Pago (Pix).
- ✅ Geração automática de QR Code para pagamento.
- ✅ Confirmação automática de pagamento.
- ✅ Check-in na portaria.
- ✅ Cardápio digital para pedidos pelo celular.
- ✅ Painel administrativo com controle financeiro.

---

## 🛠️ Tecnologias Utilizadas

- Python
- Flask
- SQLAlchemy
- PostgreSQL (Render)
- Mercado Pago SDK

---

## ⚙️ Configuração no Render

As chaves e credenciais **não ficam no código**.

Elas devem ser configuradas em:

Render Dashboard → Environment Variables

Variáveis obrigatórias:

- `DATABASE_URL`
- `MP_ACCESS_TOKEN`
- `SECRET_KEY`

---

## ▶️ Como Executar Localmente

1. Instale as dependências:
