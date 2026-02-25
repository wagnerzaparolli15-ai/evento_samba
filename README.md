# Bafafá 2026 - Sistema Enterprise Híbrido 🎷🚀

O sistema de gestão definitiva para o evento Bafafá 2026, unindo tecnologia de ponta, acessibilidade e sofisticação.

## 💎 Diferenciais Tecnológicos
- **Arquitetura Híbrida**: Venda de ingressos online, bar digital com carteira própria (Wallet) e suporte total para o "Lado B" (operação manual).
- **Wallet System**: Clientes podem carregar saldo via Pix ou no caixa físico para compras instantâneas.
- **Interface Glassmorphism**: Visual de alto nível com efeitos de desfoque e transparência (vidro), otimizado para iPhone 17 e Android 11+.
- **PDV Estilo Zé Delivery**: Vitrine de produtos com interação fluida via AJAX (sem recarregamento de página) e resposta tátil (vibração).
- **Scanner Inteligente**: Portaria com controle de bateria (câmera on/off) e sistema de "Desfazer Check-in".

## 🚀 Como Iniciar
1. Realize o deploy no Render.
2. Configure as variáveis de ambiente:
   - `DATABASE_URL`: Link do banco PostgreSQL.
   - `MP_ACCESS_TOKEN`: Token do Mercado Pago.
   - `SECRET_KEY`: Chave de segurança do Flask.
3. **MUITO IMPORTANTE**: Após o deploy, acesse o link de sincronização para criar o banco de dados e a vitrine master:
   `https://evento-samba.onrender.com/reset-bruto-bafafa`

## 🛠️ Operação
- **Admin Master**: Controle financeiro em tempo real (Receita, Custos, Lucro), gestão de estoque e recarga de saldo de clientes.
- **Portaria**: Validação de ingressos via QR Code com modo de economia de energia.
- **Super Barman**: Tela de pedidos em tempo real e PDV manual para clientes sem smartphone.

---
Desenvolvido para Wagner Master - Bafafá 2026.