-- SQLite schema para Food Delivery System alinhado ao app.py

-- Tabela de Usuários (campos em português)
CREATE TABLE IF NOT EXISTS user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE,
    senha VARCHAR(200),
    endereco VARCHAR(200),
    telefone VARCHAR(20),
    eh_restaurante BOOLEAN DEFAULT 0,
    eh_admin BOOLEAN DEFAULT 0,
    id_social VARCHAR(100) UNIQUE,
    provedor_social VARCHAR(20),
    codigo_verificacao VARCHAR(6),
    codigo_verificacao_expira_em DATETIME,
    verificado BOOLEAN DEFAULT 0
);

-- Tabela de Restaurantes
CREATE TABLE IF NOT EXISTS restaurant (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_dono INTEGER NOT NULL,
    nome VARCHAR(100) NOT NULL,
    descricao TEXT,
    categoria VARCHAR(50),
    taxa_entrega REAL DEFAULT 0.0,
    tempo_entrega INTEGER,
    avaliacao REAL DEFAULT 0.0,
    logo VARCHAR(200),
    endereco VARCHAR(200) NOT NULL,
    telefone VARCHAR(20),
    url_imagem VARCHAR(200),
    FOREIGN KEY (id_dono) REFERENCES user(id) ON DELETE CASCADE
);

-- Tabela de Itens do Menu
CREATE TABLE IF NOT EXISTS menu_item (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    restaurante_id INTEGER NOT NULL,
    nome VARCHAR(100) NOT NULL,
    descricao TEXT,
    preco REAL NOT NULL,
    imagem VARCHAR(200),
    url_imagem VARCHAR(200),
    categoria VARCHAR(50),
    disponivel BOOLEAN DEFAULT 1,
    FOREIGN KEY (restaurante_id) REFERENCES restaurant(id) ON DELETE CASCADE
);

-- Tabela de Pedidos
CREATE TABLE IF NOT EXISTS "order" (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL,
    restaurante_id INTEGER NOT NULL,
    endereco_id INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    subtotal REAL NOT NULL,
    taxa_entrega REAL NOT NULL DEFAULT 0.0,
    total REAL NOT NULL,
    metodo_pagamento VARCHAR(50) NOT NULL,
    observacoes TEXT,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES user(id) ON DELETE CASCADE,
    FOREIGN KEY (restaurante_id) REFERENCES restaurant(id) ON DELETE CASCADE,
    FOREIGN KEY (endereco_id) REFERENCES user_address(id) ON DELETE CASCADE
);

-- Tabela de Itens do Pedido
CREATE TABLE IF NOT EXISTS order_item (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pedido_id INTEGER NOT NULL,
    item_menu_id INTEGER NOT NULL,
    quantidade INTEGER NOT NULL,
    preco REAL NOT NULL,
    FOREIGN KEY (pedido_id) REFERENCES "order"(id) ON DELETE CASCADE,
    FOREIGN KEY (item_menu_id) REFERENCES menu_item(id) ON DELETE CASCADE
);

-- Tabela de Endereços de Usuário
CREATE TABLE IF NOT EXISTS user_address (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL,
    nome VARCHAR(100) NOT NULL,
    rua VARCHAR(200) NOT NULL,
    numero VARCHAR(20) NOT NULL,
    complemento VARCHAR(100),
    bairro VARCHAR(100) NOT NULL,
    cidade VARCHAR(100) NOT NULL,
    estado VARCHAR(50) NOT NULL,
    cep VARCHAR(20) NOT NULL,
    referencia VARCHAR(200),
    padrao BOOLEAN DEFAULT 0,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES user(id) ON DELETE CASCADE
);

-- Carrinho e Itens do Carrinho
CREATE TABLE IF NOT EXISTS cart (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL,
    restaurante_id INTEGER NOT NULL,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES user(id) ON DELETE CASCADE,
    FOREIGN KEY (restaurante_id) REFERENCES restaurant(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS cart_item (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    carrinho_id INTEGER NOT NULL,
    item_menu_id INTEGER NOT NULL,
    quantidade INTEGER NOT NULL,
    preco REAL NOT NULL,
    FOREIGN KEY (carrinho_id) REFERENCES cart(id) ON DELETE CASCADE,
    FOREIGN KEY (item_menu_id) REFERENCES menu_item(id) ON DELETE CASCADE
);

-- Favoritos de Restaurantes
CREATE TABLE IF NOT EXISTS restaurant_favorite (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL,
    restaurante_id INTEGER NOT NULL,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (usuario_id, restaurante_id),
    FOREIGN KEY (usuario_id) REFERENCES user(id) ON DELETE CASCADE,
    FOREIGN KEY (restaurante_id) REFERENCES restaurant(id) ON DELETE CASCADE
);

-- Favoritos de Produtos
CREATE TABLE IF NOT EXISTS product_favorite (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL,
    item_menu_id INTEGER NOT NULL,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (usuario_id, item_menu_id),
    FOREIGN KEY (usuario_id) REFERENCES user(id) ON DELETE CASCADE,
    FOREIGN KEY (item_menu_id) REFERENCES menu_item(id) ON DELETE CASCADE
);

-- Tabela para OAuth (autenticação social via Flask-Dance)
CREATE TABLE IF NOT EXISTS oauth (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider VARCHAR(50) NOT NULL,
    token TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
);

-- Índices para melhorar a performance
CREATE INDEX IF NOT EXISTS idx_user_email ON user(email);
CREATE INDEX IF NOT EXISTS idx_restaurant_owner ON restaurant(id_dono);
CREATE INDEX IF NOT EXISTS idx_menu_item_restaurant ON menu_item(restaurante_id);
CREATE INDEX IF NOT EXISTS idx_order_user ON "order"(usuario_id);
CREATE INDEX IF NOT EXISTS idx_order_restaurant ON "order"(restaurante_id);
CREATE INDEX IF NOT EXISTS idx_order_item_order ON order_item(pedido_id);
CREATE INDEX IF NOT EXISTS idx_order_item_menu_item ON order_item(item_menu_id);
CREATE INDEX IF NOT EXISTS idx_user_address_user ON user_address(usuario_id);
CREATE INDEX IF NOT EXISTS idx_cart_user ON cart(usuario_id);
CREATE INDEX IF NOT EXISTS idx_cart_restaurant ON cart(restaurante_id);
CREATE INDEX IF NOT EXISTS idx_cart_item_cart ON cart_item(carrinho_id);
CREATE INDEX IF NOT EXISTS idx_cart_item_menu ON cart_item(item_menu_id);
CREATE INDEX IF NOT EXISTS idx_restaurant_fav_user ON restaurant_favorite(usuario_id);
CREATE INDEX IF NOT EXISTS idx_product_fav_user ON product_favorite(usuario_id);
CREATE INDEX IF NOT EXISTS idx_oauth_user ON oauth(user_id);

-- Dados de exemplo
INSERT INTO user (nome, email, senha, endereco, telefone, eh_restaurante, eh_admin, verificado)
VALUES ('Demo Restaurante', 'demo@restaurant.com', 'pbkdf2:sha256:demo', 'Rua Exemplo, 123', '(11) 99999-9999', 1, 0, 1);

INSERT INTO user (nome, email, senha, endereco, telefone, eh_restaurante, eh_admin, verificado)
VALUES ('Cliente Exemplo', 'cliente@exemplo.com', 'pbkdf2:sha256:demo', 'Rua Cliente, 456', '(11) 88888-8888', 0, 0, 1);

INSERT INTO restaurant (id_dono, nome, descricao, categoria, taxa_entrega, tempo_entrega, avaliacao, logo, endereco, telefone, url_imagem)
VALUES (1, 'Pizzaria Demo', 'A melhor pizza da cidade', 'Italiana', 5.99, 30, 4.5, NULL, 'Rua Pizza, 456', '(11) 88888-8888', 'https://via.placeholder.com/600x300');

INSERT INTO menu_item (restaurante_id, nome, descricao, preco, url_imagem, categoria, disponivel)
VALUES (1, 'Pizza Margherita', 'Clássica com tomate, mozzarella e manjericão', 39.90, 'https://via.placeholder.com/300', 'Pizza', 1);

INSERT INTO user_address (usuario_id, nome, rua, numero, bairro, cidade, estado, cep, padrao)
VALUES (2, 'Casa', 'Rua Cliente', '456', 'Centro', 'São Paulo', 'SP', '00000-000', 1);

INSERT INTO "order" (usuario_id, restaurante_id, endereco_id, status, subtotal, taxa_entrega, total, metodo_pagamento)
VALUES (2, 1, 1, 'delivered', 39.90, 0.0, 39.90, 'cash');

INSERT INTO order_item (pedido_id, item_menu_id, quantidade, preco)
VALUES (1, 1, 1, 39.90);