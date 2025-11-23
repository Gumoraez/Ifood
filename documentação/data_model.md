# Modelo de Dados Físico — Food Delivery

Este documento descreve o modelo físico (tabelas, colunas, tipos, chaves e índices) das entidades envolvidas nesta entrega, alinhado ao script `create_database.sql` e ao código `app.py`.

## Tabela `user`
- id: INTEGER, PK, AUTOINCREMENT
- nome: VARCHAR(100), NOT NULL
- email: VARCHAR(100), UNIQUE
- senha: VARCHAR(200)
- endereco: VARCHAR(200)
- telefone: VARCHAR(20)
- eh_restaurante: BOOLEAN, DEFAULT 0
- eh_admin: BOOLEAN, DEFAULT 0
- id_social: VARCHAR(100), UNIQUE
- provedor_social: VARCHAR(20)
- codigo_verificacao: VARCHAR(6)
- codigo_verificacao_expira_em: DATETIME
- verificado: BOOLEAN, DEFAULT 0
- Índices: `idx_user_email (email)`

Relacionamentos:
- Referenciada por `restaurant.id_dono` (ON DELETE CASCADE)
- Referenciada por `order.usuario_id` (ON DELETE CASCADE)
- Referenciada por `user_address.usuario_id` (ON DELETE CASCADE)
- Referenciada por `oauth.user_id` (ON DELETE CASCADE)

## Tabela `restaurant`
- id: INTEGER, PK, AUTOINCREMENT
- id_dono: INTEGER, NOT NULL, FK → user(id)
- nome: VARCHAR(100), NOT NULL
- descricao: TEXT
- categoria: VARCHAR(50)
- taxa_entrega: REAL, DEFAULT 0.0
- tempo_entrega: INTEGER
- avaliacao: REAL, DEFAULT 0.0
- logo: VARCHAR(200)
- endereco: VARCHAR(200), NOT NULL
- telefone: VARCHAR(20)
- url_imagem: VARCHAR(200)
- Índices: `idx_restaurant_owner (id_dono)`

Relacionamentos:
- Referencia `user(id)`
- Referenciada por `menu_item.restaurante_id`
- Referenciada por `order.restaurante_id`

## Tabela `menu_item`
- id: INTEGER, PK, AUTOINCREMENT
- restaurante_id: INTEGER, NOT NULL, FK → restaurant(id)
- nome: VARCHAR(100), NOT NULL
- descricao: TEXT
- preco: REAL, NOT NULL
- imagem: VARCHAR(200)
- url_imagem: VARCHAR(200)
- categoria: VARCHAR(50)
- disponivel: BOOLEAN, DEFAULT 1
- Índices: `idx_menu_item_restaurant (restaurante_id)`

Relacionamentos:
- Referencia `restaurant(id)`
- Referenciada por `order_item.item_menu_id`

## Tabela `order`
- id: INTEGER, PK, AUTOINCREMENT
- usuario_id: INTEGER, NOT NULL, FK → user(id)
- restaurante_id: INTEGER, NOT NULL, FK → restaurant(id)
- endereco_id: INTEGER, NOT NULL, FK → user_address(id)
- status: VARCHAR(20), NOT NULL, DEFAULT 'pending'
- subtotal: REAL, NOT NULL
- taxa_entrega: REAL, NOT NULL, DEFAULT 0.0
- total: REAL, NOT NULL
- metodo_pagamento: VARCHAR(50), NOT NULL
- observacoes: TEXT
- criado_em: DATETIME, NOT NULL, DEFAULT CURRENT_TIMESTAMP
- Índices: `idx_order_user (usuario_id)`, `idx_order_restaurant (restaurante_id)`

Relacionamentos:
- Referencia `user(id)`, `restaurant(id)` e `user_address(id)`
- Referenciada por `order_item.pedido_id`

## Tabela `order_item`
- id: INTEGER, PK, AUTOINCREMENT
- pedido_id: INTEGER, NOT NULL, FK → order(id)
- item_menu_id: INTEGER, NOT NULL, FK → menu_item(id)
- quantidade: INTEGER, NOT NULL
- preco: REAL, NOT NULL
- Índices: `idx_order_item_order (pedido_id)`, `idx_order_item_menu_item (item_menu_id)`

Relacionamentos:
- Referencia `order(id)` e `menu_item(id)`

## Tabela `user_address`
- id: INTEGER, PK, AUTOINCREMENT
- usuario_id: INTEGER, NOT NULL, FK → user(id)
- nome: VARCHAR(100), NOT NULL
- rua: VARCHAR(200), NOT NULL
- numero: VARCHAR(20), NOT NULL
- complemento: VARCHAR(100)
- bairro: VARCHAR(100), NOT NULL
- cidade: VARCHAR(100), NOT NULL
- estado: VARCHAR(50), NOT NULL
- cep: VARCHAR(20), NOT NULL
- referencia: VARCHAR(200)
- padrao: BOOLEAN, DEFAULT 0
- criado_em: DATETIME, NOT NULL, DEFAULT CURRENT_TIMESTAMP
- Índices: `idx_user_address_user (usuario_id)`

Relacionamentos:
- Referenciada por `order.endereco_id`

## Tabelas `cart` e `cart_item`
- `cart`: id, usuario_id, restaurante_id, criado_em, atualizado_em
- `cart_item`: id, carrinho_id, item_menu_id, quantidade, preco
- Índices: `idx_cart_user`, `idx_cart_restaurant`, `idx_cart_item_cart`, `idx_cart_item_menu`

## Tabelas de Favoritos
- `restaurant_favorite`: id, usuario_id, restaurante_id, criado_em; UNIQUE(usuario_id, restaurante_id)
- `product_favorite`: id, usuario_id, item_menu_id, criado_em; UNIQUE(usuario_id, item_menu_id)

## Tabela `oauth`
- id: INTEGER, PK, AUTOINCREMENT
- provider: VARCHAR(50), NOT NULL
- token: TEXT, NOT NULL
- user_id: INTEGER, NOT NULL, FK → user(id)
- Índices: `idx_oauth_user (user_id)`

Relacionamentos:
- Referencia `user(id)`

## Observações
- Todas as FKs usam `ON DELETE CASCADE` para manter integridade ao remover usuários/restaurantes.
- A tabela `order` usa aspas no SQL (`"order"`) por ser palavra reservada; em documentos mantemos `order` por clareza.
- Campos de mídia usam `imagem` e `url_imagem` no padrão português.