# Autenticação e Fluxo de Pedidos

Este documento descreve as funcionalidades e regras de negócio dos módulos de autenticação e de solicitação/acompanhamento de pedidos do sistema iFood Replica.

1) Autenticação
- Registro de usuário (cliente): formulário com nome, email, senha; persiste no banco e inicia sessão automaticamente após registro. <mcfile name="app.py" path="C:\Users\Gustavo Moraes\Documents\Ifood!\app.py"></mcfile>
- Registro de restaurante: cria conta marcada como proprietária de restaurante e redireciona para criação do restaurante. <mcsymbol name="register_restaurant" filename="app.py" path="C:\Users\Gustavo Moraes\Documents\Ifood!\app.py" startline="200" type="function"></mcsymbol>
- Login tradicional: valida email/senha e inicia sessão com Flask-Login; Logout encerra a sessão. <mcfile name="login.html" path="C:\Users\Gustavo Moraes\Documents\Ifood!\templates\login.html"></mcfile> <mcfile name="app.py" path="C:\Users\Gustavo Moraes\Documents\Ifood!\app.py"></mcfile>
- Login social (Google/Facebook): se email não existir, cria nova conta com campos social_id/social_provider e faz login; caso exista, associa login e inicia sessão. <mcsymbol name="google_login" filename="app.py" path="C:\Users\Gustavo Moraes\Documents\Ifood!\app.py" startline="225" type="function"></mcsymbol> <mcsymbol name="facebook_login" filename="app.py" path="C:\Users\Gustavo Moraes\Documents\Ifood!\app.py" startline="257" type="function"></mcsymbol>
- Perfis e permissões: campos is_admin e is_restaurant controlam acesso; rotas protegidas exigem login e validam dono (owner) do recurso ou admin.

2) Fluxo de Pedido (da escolha à entrega)
- Escolha de restaurante e itens: página do restaurante exibe cardápio e permite adicionar itens ao carrinho via JS. <mcsymbol name="restaurant" filename="app.py" path="C:\Users\Gustavo Moraes\Documents\Ifood!\app.py" startline="292" type="function"></mcsymbol> <mcfile name="restaurant.html" path="C:\Users\Gustavo Moraes\Documents\Ifood!\templates\restaurant.html"></mcfile> <mcfile name="static/js/main.js" path="C:\Users\Gustavo Moraes\Documents\Ifood!\static\js\main.js"></mcfile>
- Carrinho e Checkout: o carrinho é gerenciado no cliente; o checkout envia POST com itens/total/restaurant_id para criar pedido (Order) e itens (OrderItem). <mcsymbol name="checkout" filename="app.py" path="C:\Users\Gustavo Moraes\Documents\Ifood!\app.py" startline="315" type="function"></mcsymbol> <mcfile name="checkout.html" path="C:\Users\Gustavo Moraes\Documents\Ifood!\templates\checkout.html"></mcfile>
- Acompanhamento do cliente: lista “Meus Pedidos” mostra pedidos do usuário com itens, total e status. <mcsymbol name="orders" filename="app.py" path="C:\Users\Gustavo Moraes\Documents\Ifood!\app.py" startline="353" type="function"></mcsymbol> <mcfile name="orders.html" path="C:\Users\Gustavo Moraes\Documents\Ifood!\templates\orders.html"></mcfile>
- Cancelamento pelo cliente: apenas pedidos com status pending podem ser cancelados pelo dono do pedido ou por admin. <mcsymbol name="cancel_order" filename="app.py" path="C:\Users\Gustavo Moraes\Documents\Ifood!\app.py" startline="359" type="function"></mcsymbol>
- Acompanhamento do restaurante (owner/admin): página de pedidos do restaurante exibe todos os pedidos e permite atualizar status. <mcsymbol name="restaurant_orders" filename="app.py" path="C:\Users\Gustavo Moraes\Documents\Ifood!\app.py" startline="377" type="function"></mcsymbol> <mcfile name="restaurant_orders.html" path="C:\Users\Gustavo Moraes\Documents\Ifood!\templates\restaurant_orders.html"></mcfile>
- Atualização de status (owner/admin): valida transições na sequência pending → preparing → delivering → delivered; cancelamento só é permitido quando o pedido está pending. <mcsymbol name="update_order_status" filename="app.py" path="C:\Users\Gustavo Moraes\Documents\Ifood!\app.py" startline="389" type="function"></mcsymbol>

3) Regras de negócio de pedidos
- Status possíveis: pending, preparing, delivering, delivered, cancelled. <mcfile name="app.py" path="C:\Users\Gustavo Moraes\Documents\Ifood!\app.py"></mcfile>
- Criação de pedido: grava Order (user_id, restaurant_id, total, delivery_address) e OrderItem (menu_item_id, quantity, price) para cada item do carrinho.
- Cancelamento: permitido ao cliente dono do pedido ou admin, somente se status == pending; ao cancelar, status torna-se cancelled.
- Atualização de status: somente owner do restaurante ou admin; transições devem respeitar a ordem incremental (pending→preparing→delivering→delivered). Cancelamento permitido apenas em pending.
- Visualização: cliente vê seus pedidos e pode cancelar os pendentes; owner/admin vê pedidos do seu restaurante, edita status e pode cancelar pendentes.

4) Segurança e conformidade
- Sessão: gerenciada por Flask-Login, rotas @login_required protegem ações sensíveis.
- Permissões: validação consistente de owner/admin nas rotas de restaurante, itens do menu e pedidos.
- Sugestões: adicionar CSRF tokens em formulários, auditoria de eventos (logs), e taxa de pedidos limitada por usuário para evitar abuso.

5) Referências de dados e rotas
- Modelos principais: User, Restaurant, MenuItem, Order, OrderItem, OAuth. <mcfile name="create_database.sql" path="C:\Users\Gustavo Moraes\Documents\Ifood!\documentation\create_database.sql"></mcfile>
- Banco de dados: SQLite por padrão (configurado em SQLALCHEMY_DATABASE_URI). <mcfile name="app.py" path="C:\Users\Gustavo Moraes\Documents\Ifood!\app.py"></mcfile>