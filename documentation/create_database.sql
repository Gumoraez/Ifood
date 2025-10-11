-- SQLite schema para iFood Replica alinhado ao app.py

-- Tabela de Usuários
CREATE TABLE IF NOT EXISTS user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(200),
    address VARCHAR(200),
    phone VARCHAR(20),
    is_restaurant BOOLEAN DEFAULT 0,
    is_admin BOOLEAN DEFAULT 0,
    social_id VARCHAR(100) UNIQUE,
    social_provider VARCHAR(20)
);

-- Tabela de Restaurantes
CREATE TABLE IF NOT EXISTS restaurant (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id INTEGER NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    category VARCHAR(50),
    delivery_fee REAL DEFAULT 0.0,
    delivery_time INTEGER,
    rating REAL DEFAULT 0.0,
    logo VARCHAR(200),
    address VARCHAR(200) NOT NULL,
    phone VARCHAR(20),
    image_url VARCHAR(200),
    FOREIGN KEY (owner_id) REFERENCES user(id) ON DELETE CASCADE
);

-- Tabela de Itens do Menu
CREATE TABLE IF NOT EXISTS menu_item (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    restaurant_id INTEGER NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    price REAL NOT NULL,
    image VARCHAR(200),
    image_url VARCHAR(200),
    category VARCHAR(50),
    available BOOLEAN DEFAULT 1,
    FOREIGN KEY (restaurant_id) REFERENCES restaurant(id) ON DELETE CASCADE
);

-- Tabela de Pedidos
CREATE TABLE IF NOT EXISTS "order" (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    restaurant_id INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    total REAL NOT NULL,
    delivery_address VARCHAR(200) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE,
    FOREIGN KEY (restaurant_id) REFERENCES restaurant(id) ON DELETE CASCADE
);

-- Tabela de Itens do Pedido
CREATE TABLE IF NOT EXISTS order_item (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    menu_item_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    price REAL NOT NULL,
    FOREIGN KEY (order_id) REFERENCES "order"(id) ON DELETE CASCADE,
    FOREIGN KEY (menu_item_id) REFERENCES menu_item(id) ON DELETE CASCADE
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
CREATE INDEX IF NOT EXISTS idx_restaurant_owner ON restaurant(owner_id);
CREATE INDEX IF NOT EXISTS idx_menu_item_restaurant ON menu_item(restaurant_id);
CREATE INDEX IF NOT EXISTS idx_order_user ON "order"(user_id);
CREATE INDEX IF NOT EXISTS idx_order_restaurant ON "order"(restaurant_id);
CREATE INDEX IF NOT EXISTS idx_order_item_order ON order_item(order_id);
CREATE INDEX IF NOT EXISTS idx_order_item_menu_item ON order_item(menu_item_id);
CREATE INDEX IF NOT EXISTS idx_oauth_user ON oauth(user_id);

-- Dados de exemplo
INSERT INTO user (name, email, password, address, phone, is_restaurant, is_admin)
VALUES ('Demo Restaurante', 'demo@restaurant.com', 'pbkdf2:sha256:demo', 'Rua Exemplo, 123', '(11) 99999-9999', 1, 0);

INSERT INTO user (name, email, password, address, phone, is_restaurant, is_admin)
VALUES ('Cliente Exemplo', 'cliente@exemplo.com', 'pbkdf2:sha256:demo', 'Rua Cliente, 456', '(11) 88888-8888', 0, 0);

INSERT INTO restaurant (owner_id, name, description, category, delivery_fee, delivery_time, rating, logo, address, phone, image_url)
VALUES (1, 'Pizzaria Demo', 'A melhor pizza da cidade', 'Italiana', 5.99, 30, 4.5, NULL, 'Rua Pizza, 456', '(11) 88888-8888', 'https://via.placeholder.com/600x300');

INSERT INTO menu_item (restaurant_id, name, description, price, image_url, category, available)
VALUES (1, 'Pizza Margherita', 'Clássica com tomate, mozzarella e manjericão', 39.90, 'https://via.placeholder.com/300', 'Pizza', 1);

INSERT INTO "order" (user_id, restaurant_id, status, total, delivery_address)
VALUES (2, 1, 'delivered', 39.90, 'Rua Cliente, 456');

INSERT INTO order_item (order_id, menu_item_id, quantity, price)
VALUES (1, 1, 1, 39.90);