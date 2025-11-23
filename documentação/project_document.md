# Projeto Food Delivery — Documento Consolidado

## 1. Escopo do Projeto (Objetivo)
- Entregar um sistema web de entrega de comida com:
  - Autenticação de usuários (cliente e conta de restaurante), login social (Google/Facebook) e verificação de contato via código (email/SMS/WhatsApp).
  - Cadastro de restaurante e gestão de cardápio.
  - Seleção de itens, carrinho, checkout, criação de pedido, acompanhamento e atualização de status até a entrega.
  - Administração básica de usuários, endereços e favoritos.

## 2. Sumário
- 1. Escopo do Projeto (Objetivo)
- 2. Sumário
- 3. Diagrama da Arquitetura
- 4. Requisitos/Funcionalidades
- 5. Diagrama do Modelo de Dados Físico
- 6. Script de Criação do Banco de Dados
- 7. Funcionalidades implementadas (prints e explicações)

## 3. Diagrama da Arquitetura
- Arquivo: `architecture_diagram.svg`
- Hosts/SO: Ambiente de desenvolvimento local em `Windows` (PowerShell), servidor Flask em `localhost`.
- Componentes de Software e versões:
  - `Flask 2.3.3`
  - `Werkzeug 2.3.7`
  - `Flask-SQLAlchemy 3.1.1` + `SQLAlchemy 2.0.21`
  - `Flask-Login 0.6.2`
  - `Flask-WTF 1.2.1` + `email-validator 2.0.0`
  - `Flask-Dance 5.1.0` (OAuth Google/Facebook)
  - `Flask-Mail 0.9.1` (SMTP)
  - `python-dotenv 1.0.0`
  - Bibliotecas auxiliares: `requests`, `oauthlib`, `blinker`, `Pillow`
- Integrações:
  - SMTP (email) via Flask-Mail
  - Twilio (SMS/WhatsApp) — configurável por variáveis de ambiente
  - OAuth Google/Facebook via Flask-Dance

## 4. Requisitos/Funcionalidades
### 4.1 Autenticação
- Registro de usuário (cliente) e de restaurante.
- Login tradicional e logout; login social Google/Facebook.
- Verificação de contato: envio de código por email/SMS/WhatsApp e validação.
- Perfis: `is_admin`, `is_restaurant` controlam acesso a rotas.

Regras da funcionalidade:
- Códigos têm 6 dígitos e expiração definida; reenvio permitido com recomendação de cooldown.
- Ações sensíveis (ex.: finalizar pedido) requerem usuário verificado.
- Login social cria/associa conta se o email não existir/existir.

Campos necessários (BD com nomes em português):
- Registro usuário: `nome`, `email`, `senha`, `endereco`, `telefone`.
- Registro restaurante (conta): `nome`, `email`, `senha`, `telefone`; depois dados do `restaurant`.
- Verificação: método (email/telefone) e código de 6 dígitos.

Regras de validação dos campos:
- `email`: formato válido; único.
- `senha`: tamanho mínimo (ex.: 6) e hash ao persistir.
- `telefone`: formato consistente (preferível E.164 para SMS/WhatsApp).
- `nome`, `endereco`, `restaurant.nome`: não vazios.

Campos obrigatórios:
- Registro usuário: `nome`, `email`, `senha`, `endereco`, `telefone`.
- Registro restaurante: `nome`, `email`, `senha`, `telefone`.
- Criação de restaurante: `id_dono`, `nome`, `endereco`.

### 4.2 Fluxo de Pedido
- Escolher restaurante e itens, adicionar ao carrinho, checkout, criação de pedido, acompanhamento.
- Cancelamento pelo cliente quando `status = pending`.
- Atualização de status pelo owner/admin: `pending → preparing → delivering → delivered`; cancelamento apenas em `pending`.

Campos necessários no checkout/pedido:
- `user_id`, `restaurant_id`, `address_id`, `items[{menu_item_id, quantity, price}]`, `subtotal`, `delivery_fee`, `total`, `payment_method`, `notes (opcional)`.

Validação e obrigatoriedade:
- `user_id`, `restaurant_id`, `address_id`: obrigatórios e válidos.
- `items`: ao menos um item; `quantity >= 1`; `price` do momento.
- `payment_method`: um dos `credit_card`, `debit_card`, `pix`, `cash`.
- Transições de status devem ser sequenciais; cancelamento apenas em `pending`.

### 4.3 Endereços e Favoritos
- Endereços: CRUD completo, um default por usuário.
- Favoritos de restaurante: marcar/desmarcar; único por par (`user_id`, `restaurant_id`).
- Favoritos de produtos: marcar/desmarcar; único por par (`user_id`, `menu_item_id`).

### 4.4 Consultas e Filtros
- Restaurantes: busca, categoria, favoritos, "Perto de mim".
- Produtos globais (`/products`): busca, categoria, preço, disponibilidade, ordenação, favoritos e "Perto de mim" com raio.

## 5. Diagrama do Modelo de Dados Físico
- Arquivo: `data_model.svg`
- Referência detalhada: `data_model.md`
- Cardinalidades principais:
  - `User 1:N Restaurant` (owner)
  - `Restaurant 1:N MenuItem`
  - `User 1:N Order`
  - `Restaurant 1:N Order`
  - `Order 1:N OrderItem`
  - `User 1:N UserAddress`; `UserAddress 1:N Order`
  - `User 1:N OAuth`

Campos, tipos, tamanhos, obrigatoriedade:
- Ver `data_model.md` para cada tabela (`user`, `restaurant`, `menu_item`, `order`, `order_item`, `user_address`, `oauth`, `favorites`).

## 6. Script de Criação do Banco de Dados
- Arquivo: `create_database.sql`
- Conteúdo: DDL completo das tabelas, FKs com `ON DELETE CASCADE`, índices e dados de exemplo.

## 7. Funcionalidades Implementadas (prints e explicações)
- Páginas/Templates:
  - `templates/register.html`: Formulário de registro de usuário.
  - `templates/restaurant_register.html` e `templates/restaurant_form.html`: criação de conta e restaurante.
  - `templates/login.html`: login; links para social.
  - `templates/restaurant.html`: cardápio e adicionar ao carrinho.
  - `templates/cart.html`: visualizar e ajustar carrinho.
  - `templates/checkout.html`: finalizar pedido.
  - `templates/orders.html`: acompanhar e cancelar pedido.
  - `templates/restaurant_orders.html`: owner/admin atualizam status.
  - `templates/verify_code.html`: verificação de código.
  - Demais CRUDs: `menu_items.html`, `menu_item_form.html`, `addresses.html`, `address_form.html`, `favorites.html`, `users.html`, `user_detail.html`.

- Rotas principais (referência):
  - Autenticação: `/register`, `/login`, `/logout`, `/verify-code/<user_id>`, `/resend-code/<user_id>`, `/login/google`, `/login/facebook`.
  - Restaurante e Cardápio: `/restaurants`, `/restaurants/new`, `/restaurants/<id>/edit`, `/restaurants/<id>/delete`, `/restaurants/<id>/menu`, `/restaurants/<id>/menu/new`, `/menu-items/<id>/edit`, `/menu-items/<id>/delete`.
  - Carrinho/Pedido: `/cart`, `/add_to_cart`, `/update_cart_item`, `/remove_from_cart`, `/clear_cart`, `/checkout`, `/orders`, `/orders/<id>/cancel`, `/orders/<id>/status`, `/orders/<id>/invoice`.
  - Endereços: `/addresses`, `/addresses/new`, `/addresses/<id>/edit`, `/addresses/<id>/delete`, `/addresses/<id>/set-default`.
  - Favoritos: `/restaurants/<id>/favorite`, `/restaurants/<id>/unfavorite`, `/favorites`.
  - Produtos globais e favoritos: `/products`, `/products/<id>/favorite`, `/products/<id>/unfavorite`.
  - API Mobile (CRUD restaurantes): `/api/restaurants` (GET/POST), `/api/restaurants/<id>` (PUT/DELETE).
  - Debug: `/debug/send-email`, `/debug/db-info`, `/debug/reset-db`, `/debug/seed-demo`.

- Explicação breve do funcionamento do código:
  - Autenticação/Verificação: `Flask-Login` gerencia sessão; `send_email_code` usa `Flask-Mail` com fallback SMTP; SMS via Twilio quando configurado.
  - Pedidos: `Order` agrega `OrderItem`, calcula `subtotal/delivery_fee/total`; status e transições são validadas em rota dedicada.
  - Carrinho: `Cart` e `CartItem` guardam itens por usuário/restaurante, com subtotal e contagem.
  - Endereços: `UserAddress` com campo `is_default` e relação 1:N com `Order`.
  - Favoritos: restrição única por usuário/restaurante e usuário/item.
  - API Mobile: endpoints JSON para listar/criar/editar/excluir restaurantes, integrando diretamente ao banco via SQLAlchemy.

- Prints de tela:
  - Inserir capturas em `screenshots/` dos templates acima (registro, login, restaurante, carrinho, checkout, pedidos, verificação, etc.).
  - Sugestão de nomes: `01-register.png`, `02-login.png`, `03-restaurant.png`, `04-cart.png`, `05-checkout.png`, `06-orders.png`, `07-verify-code.png`, `08-restaurant-orders.png`.

## Anexos e Referências
- Documento de regras: `auth_and_orders.md`
- Diagrama arquitetura: `architecture_diagram.svg`
- Modelo físico (detalhado): `data_model.md`
- Diagrama do modelo: `data_model.svg`
- Script SQL: `create_database.sql`