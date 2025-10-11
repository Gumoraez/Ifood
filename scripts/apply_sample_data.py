import os
import sqlite3

DB_PATH = 'ifood.db'
ALT_PATH = os.path.join('instance', 'ifood.db')
DB = DB_PATH if os.path.exists(DB_PATH) else ALT_PATH

print('Usando banco:', DB)

con = sqlite3.connect(DB)
con.execute('PRAGMA foreign_keys = ON')
cur = con.cursor()

# Helpers idempotentes

def get_user(email, name, is_restaurant, address, phone):
    row = cur.execute('SELECT id FROM user WHERE email=?', (email,)).fetchone()
    if row:
        return row[0]
    cur.execute(
        'INSERT INTO user (name,email,password,address,phone,is_restaurant,is_admin) VALUES (?,?,?,?,?,?,0)',
        (name, email, 'pbkdf2:sha256:demo', address, phone, is_restaurant)
    )
    con.commit()
    return cur.lastrowid


def get_restaurant(owner_id, name, description, category, delivery_fee, delivery_time, rating, logo, address, phone, image_url):
    row = cur.execute('SELECT id FROM restaurant WHERE name=?', (name,)).fetchone()
    if row:
        return row[0]
    cur.execute(
        'INSERT INTO restaurant (owner_id,name,description,category,delivery_fee,delivery_time,rating,logo,address,phone,image_url) VALUES (?,?,?,?,?,?,?,?,?,?,?)',
        (owner_id, name, description, category, delivery_fee, delivery_time, rating, logo, address, phone, image_url)
    )
    con.commit()
    return cur.lastrowid


def get_menu_item(restaurant_id, name, description, price, image_url, category):
    row = cur.execute('SELECT id FROM menu_item WHERE restaurant_id=? AND name=?', (restaurant_id, name)).fetchone()
    if row:
        return row[0]
    cur.execute(
        'INSERT INTO menu_item (restaurant_id,name,description,price,image_url,category,available) VALUES (?,?,?,?,?,?,1)',
        (restaurant_id, name, description, price, image_url, category)
    )
    con.commit()
    return cur.lastrowid


def get_order(user_id, restaurant_id, status, total):
    row = cur.execute('SELECT id FROM "order" WHERE user_id=? AND restaurant_id=? AND status=? AND total=?', (user_id, restaurant_id, status, total)).fetchone()
    if row:
        return row[0]
    delivery_address = cur.execute('SELECT address FROM user WHERE id=?', (user_id,)).fetchone()[0]
    cur.execute(
        'INSERT INTO "order" (user_id, restaurant_id, status, total, delivery_address) VALUES (?,?,?,?,?)',
        (user_id, restaurant_id, status, total, delivery_address)
    )
    con.commit()
    return cur.lastrowid


def ensure_order_item(order_id, menu_item_id, quantity, price):
    row = cur.execute('SELECT id FROM order_item WHERE order_id=? AND menu_item_id=?', (order_id, menu_item_id)).fetchone()
    if row:
        return row[0]
    cur.execute(
        'INSERT INTO order_item (order_id, menu_item_id, quantity, price) VALUES (?,?,?,?)',
        (order_id, menu_item_id, quantity, price)
    )
    con.commit()
    return cur.lastrowid

# Dados de exemplo (do script SQL)
owner_id = get_user('demo@restaurant.com', 'Demo Restaurante', 1, 'Rua Exemplo, 123', '(11) 99999-9999')
cliente_id = get_user('cliente@exemplo.com', 'Cliente Exemplo', 0, 'Rua Cliente, 456', '(11) 88888-8888')

restaurant_id = get_restaurant(owner_id, 'Pizzaria Demo', 'A melhor pizza da cidade', 'Italiana', 5.99, 30, 4.5, None, 'Rua Pizza, 456', '(11) 88888-8888', 'https://via.placeholder.com/600x300')
menu_item_id = get_menu_item(restaurant_id, 'Pizza Margherita', 'Clássica com tomate, mozzarella e manjericão', 39.90, 'https://via.placeholder.com/300', 'Pizza')

# --- Novos restaurantes e itens ---
# Sushi House
owner_sushi = get_user('owner.sushi@example.com', 'Sushi House Owner', 1, 'Av. Japão, 100', '(11) 98888-1111')
rest_sushi = get_restaurant(owner_sushi, 'Sushi House', 'Sushis frescos e pratos japoneses', 'Japonesa', 7.50, 45, 4.7, None, 'Av. Japão, 100', '(11) 98888-1111', 'https://via.placeholder.com/600x300')
get_menu_item(rest_sushi, 'Sushi Combo 12 peças', 'Seleção de 12 peças com peixes frescos', 49.90, 'https://via.placeholder.com/300', 'Sushi')
get_menu_item(rest_sushi, 'Temaki Salmão', 'Temaki de salmão com cebolinha e gergelim', 24.90, 'https://via.placeholder.com/300', 'Temaki')
get_menu_item(rest_sushi, 'Yakissoba Tradicional', 'Macarrão oriental com legumes e carne', 32.00, 'https://via.placeholder.com/300', 'Prato')

# Burger Mania
owner_burger = get_user('owner.burger@example.com', 'Burger Mania Owner', 1, 'Rua Estados Unidos, 200', '(11) 97777-2222')
rest_burger = get_restaurant(owner_burger, 'Burger Mania', 'Hambúrgueres artesanais e batatas crocantes', 'Americana', 6.90, 25, 4.4, None, 'Rua Estados Unidos, 200', '(11) 97777-2222', 'https://via.placeholder.com/600x300')
get_menu_item(rest_burger, 'Cheeseburger Clássico', 'Pão brioche, hambúrguer 160g, queijo e molho especial', 29.90, 'https://via.placeholder.com/300', 'Lanche')
get_menu_item(rest_burger, 'Duplo Bacon', 'Dois hambúrgueres, queijo cheddar e bacon crocante', 39.90, 'https://via.placeholder.com/300', 'Lanche')
get_menu_item(rest_burger, 'Batata Rústica', 'Batatas rústicas com páprica e ervas', 14.90, 'https://via.placeholder.com/300', 'Acompanhamento')

# Veggie Delight
owner_veggie = get_user('owner.veggie@example.com', 'Veggie Delight Owner', 1, 'Rua das Flores, 300', '(11) 96666-3333')
rest_veggie = get_restaurant(owner_veggie, 'Veggie Delight', 'Opções vegetarianas e veganas saborosas', 'Vegetariana', 5.00, 20, 4.6, None, 'Rua das Flores, 300', '(11) 96666-3333', 'https://via.placeholder.com/600x300')
get_menu_item(rest_veggie, 'Bowl de Quinoa', 'Quinoa, legumes grelhados e molho tahine', 27.50, 'https://via.placeholder.com/300', 'Bowl')
get_menu_item(rest_veggie, 'Hambúrguer de Grão-de-bico', 'Hambúrguer vegano com salada e molho verde', 31.00, 'https://via.placeholder.com/300', 'Lanche')
get_menu_item(rest_veggie, 'Salada Mediterrânea', 'Folhas, tomate, pepino, azeitonas e azeite', 22.00, 'https://via.placeholder.com/300', 'Salada')

# Doceria Doce Vida
owner_doceria = get_user('owner.doceria@example.com', 'Doceria Doce Vida Owner', 1, 'Rua Açúcar, 50', '(11) 95555-4444')
rest_doceria = get_restaurant(owner_doceria, 'Doceria Doce Vida', 'Bolos e doces artesanais', 'Confeitaria', 4.00, 15, 4.8, None, 'Rua Açúcar, 50', '(11) 95555-4444', 'https://via.placeholder.com/600x300')
get_menu_item(rest_doceria, 'Bolo de Chocolate', 'Bolo úmido com cobertura cremosa de chocolate', 36.00, 'https://via.placeholder.com/300', 'Bolo')
get_menu_item(rest_doceria, 'Torta de Limão', 'Torta com creme azedinho e merengue', 28.00, 'https://via.placeholder.com/300', 'Torta')
get_menu_item(rest_doceria, 'Brigadeiro Gourmet', 'Brigadeiro com chocolate belga', 4.50, 'https://via.placeholder.com/300', 'Doce')

# Taco Fiesta
owner_taco = get_user('owner.taco@example.com', 'Taco Fiesta Owner', 1, 'Av. México, 75', '(11) 94444-5555')
rest_taco = get_restaurant(owner_taco, 'Taco Fiesta', 'Tacos e burritos autênticos', 'Mexicana', 6.50, 35, 4.3, None, 'Av. México, 75', '(11) 94444-5555', 'https://via.placeholder.com/600x300')
get_menu_item(rest_taco, 'Taco de Carne', 'Taco com carne temperada, salsa e coentro', 12.00, 'https://via.placeholder.com/300', 'Taco')
get_menu_item(rest_taco, 'Burrito de Frango', 'Burrito recheado com frango, arroz e feijão', 26.00, 'https://via.placeholder.com/300', 'Burrito')
get_menu_item(rest_taco, 'Nachos Supreme', 'Nachos com queijo, jalapeño e guacamole', 22.00, 'https://via.placeholder.com/300', 'Acompanhamento')

order_id = get_order(cliente_id, restaurant_id, 'delivered', 39.90)
order_item_id = ensure_order_item(order_id, menu_item_id, 1, 39.90)

# Resumo
summary = {
    'owner_id': owner_id,
    'cliente_id': cliente_id,
    'restaurant_id': restaurant_id,
    'menu_item_id': menu_item_id,
    'order_id': order_id,
    'order_item_id': order_item_id,
    'db': DB,
}
print('Atualizado com sucesso:', summary)

# Mostrar últimos registros relevantes
print('Usuários (email,name):', cur.execute('SELECT email,name FROM user ORDER BY id DESC LIMIT 5').fetchall())
print('Restaurantes (id,name):', cur.execute('SELECT id,name FROM restaurant ORDER BY id DESC LIMIT 5').fetchall())
print('Itens de menu (id,name):', cur.execute('SELECT id,name FROM menu_item ORDER BY id DESC LIMIT 5').fetchall())
print('Pedidos (id,status,total):', cur.execute('SELECT id,status,total FROM "order" ORDER BY id DESC LIMIT 5').fetchall())
print('Itens do pedido (id,order_id,menu_item_id,qty):', cur.execute('SELECT id,order_id,menu_item_id,quantity FROM order_item ORDER BY id DESC LIMIT 5').fetchall())