from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime
from flask_dance.contrib.google import make_google_blueprint, google
from flask_dance.contrib.facebook import make_facebook_blueprint, facebook
from flask_dance.consumer.storage.sqla import OAuthConsumerMixin, SQLAlchemyStorage
from flask_dance.consumer import oauth_authorized
from sqlalchemy.orm.exc import NoResultFound
from dotenv import load_dotenv

# Carrega variáveis do .env e permite HTTP em desenvolvimento
load_dotenv()
os.environ.setdefault('OAUTHLIB_INSECURE_TRANSPORT', '1')

# Configuração da aplicação
# Configuração principal do Flask
app = Flask(__name__)
# Chave secreta para proteger sessões e CSRF em formulários
app.config['SECRET_KEY'] = 'ifood-replica-secret-key'
# Banco de dados SQLite no arquivo ifood.db (na raiz do projeto)
# Dica: se preferir, mude para dentro de instance com: 'sqlite:///instance/ifood.db'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ifood.db'
# Desativa rastreamento de modificações (melhora performance)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configurações para OAuth (Login com Google/Facebook)
# Em produção, use variáveis de ambiente reais ou um arquivo .env para guardar as credenciais
app.config['GOOGLE_OAUTH_CLIENT_ID'] = os.environ.get('GOOGLE_OAUTH_CLIENT_ID', 'seu-client-id-aqui')
app.config['GOOGLE_OAUTH_CLIENT_SECRET'] = os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET', 'seu-client-secret-aqui')
app.config['FACEBOOK_OAUTH_CLIENT_ID'] = os.environ.get('FACEBOOK_OAUTH_CLIENT_ID', 'seu-app-id-aqui')
app.config['FACEBOOK_OAUTH_CLIENT_SECRET'] = os.environ.get('FACEBOOK_OAUTH_CLIENT_SECRET', 'seu-app-secret-aqui')

# Inicialização do banco de dados (ORM SQLAlchemy)
db = SQLAlchemy(app)

# Configuração do login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Configuração dos blueprints OAuth
google_bp = make_google_blueprint(
    client_id=app.config['GOOGLE_OAUTH_CLIENT_ID'],
    client_secret=app.config['GOOGLE_OAUTH_CLIENT_SECRET'],
    scope=["profile", "email"],
    redirect_to="google_login"
)
facebook_bp = make_facebook_blueprint(
    client_id=app.config['FACEBOOK_OAUTH_CLIENT_ID'],
    client_secret=app.config['FACEBOOK_OAUTH_CLIENT_SECRET'],
    scope=["email"],
    redirect_to="facebook_login"
)

app.register_blueprint(google_bp, url_prefix="/login")
app.register_blueprint(facebook_bp, url_prefix="/login")

# Após definir os modelos, configurar persistência de tokens do Google
# (precisa da classe OAuth já carregada)
# Isto será executado ao importar o módulo
try:
    google_bp.storage = SQLAlchemyStorage(OAuth, db.session, user=current_user, user_required=False)
except NameError:
    # Em caso de ordem de definição, será reatribuído mais abaixo quando OAuth existir
    pass

# Modelos do banco de dados
# User: representa um usuário do sistema (cliente ou dono de restaurante). Suporta login social.
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=True)  # Nullable para permitir login social
    address = db.Column(db.String(200))
    phone = db.Column(db.String(20))
    is_restaurant = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)
    orders = db.relationship('Order', backref='customer', lazy=True)
    
    # Campos para autenticação social
    social_id = db.Column(db.String(100), unique=True, nullable=True)
    social_provider = db.Column(db.String(20), nullable=True)
    
    def __repr__(self):
        return f'<User {self.name}>'

class OAuth(OAuthConsumerMixin, db.Model):
    user_id = db.Column(db.Integer, db.ForeignKey(User.id))
    user = db.relationship(User)

# Configura storage do Google com SQLAlchemy assim que OAuth está disponível
try:
    google_bp.storage = SQLAlchemyStorage(OAuth, db.session, user=current_user, user_required=False)
except Exception:
    pass

# Restaurant: restaurante pertence a um usuário (owner_id) e possui itens de menu
class Restaurant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50))
    delivery_fee = db.Column(db.Float, default=0.0)
    delivery_time = db.Column(db.Integer)  # em minutos
    rating = db.Column(db.Float, default=0.0)
    logo = db.Column(db.String(200))
    address = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(20))
    image_url = db.Column(db.String(200))
    items = db.relationship('MenuItem', backref='restaurant', lazy=True)
    
    def __repr__(self):
        return f'<Restaurant {self.name}>'

# MenuItem: item do cardápio vinculado ao restaurante; pode ter image_url
class MenuItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurant.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    image = db.Column(db.String(200))
    image_url = db.Column(db.String(200))
    category = db.Column(db.String(50))
    available = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f'<MenuItem {self.name}>'

# Order: pedido com status, total e endereço; criado em created_at e possui itens (OrderItem)
class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurant.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, preparing, delivering, delivered, cancelled
    total = db.Column(db.Float, nullable=False)
    delivery_address = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    items = db.relationship('OrderItem', backref='order', lazy=True)
    
    def __repr__(self):
        return f'<Order {self.id}>'

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_item.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    
    # Relacionamento para acessar o MenuItem diretamente nos templates (item.menu_item)
    menu_item = db.relationship('MenuItem', backref='order_items')
    
    def __repr__(self):
        return f'<OrderItem {self.id}>'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Rotas
@app.route('/')
def index():
    q = request.args.get('q', '').strip()
    if q:
        restaurants = Restaurant.query.filter(
            (Restaurant.name.ilike(f"%{q}%")) |
            (Restaurant.category.ilike(f"%{q}%")) |
            (Restaurant.address.ilike(f"%{q}%"))
        ).all()
    else:
        restaurants = Restaurant.query.all()
    return render_template('index.html', restaurants=restaurants, q=q)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        address = request.form.get('address')
        phone = request.form.get('phone')
        
        user_exists = User.query.filter_by(email=email).first()
        if user_exists:
            flash('Email já cadastrado.')
            return redirect(url_for('register'))
        
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(name=name, email=email, password=hashed_password, address=address, phone=phone)
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Conta criada com sucesso!')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        if not user or not check_password_hash(user.password, password):
            flash('Verifique seu email e senha e tente novamente.')
            return redirect(url_for('login'))
        
        login_user(user)
        return redirect(url_for('index'))
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/register/restaurant', methods=['GET', 'POST'])
def register_restaurant():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        password = request.form.get('password')

        user_exists = User.query.filter_by(email=email).first()
        if user_exists:
            flash('Email já cadastrado.')
            return redirect(url_for('register_restaurant'))

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256') if password else None
        new_user = User(name=name, email=email, password=hashed_password, phone=phone, is_restaurant=True)

        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)
        flash('Conta de restaurante criada com sucesso! Agora, crie seu restaurante.')
        return redirect(url_for('create_restaurant'))

    return render_template('restaurant_register.html')

@app.route('/login/google')
def google_login():
    # Verificação preventiva: credenciais do Google configuradas?
    client_id = app.config.get('GOOGLE_OAUTH_CLIENT_ID')
    client_secret = app.config.get('GOOGLE_OAUTH_CLIENT_SECRET')
    placeholders = {'seu-client-id-aqui', 'COLE_AQUI_SEU_CLIENT_ID', None, ''}
    if client_id in placeholders or client_secret in placeholders:
        flash('Credenciais do Google não configuradas. Atualize o arquivo .env com seu Client ID e Client Secret e reinicie o servidor.', 'danger')
        try:
            expected_redirect = url_for('google.authorized', _external=True)
            flash(f'URIs esperadas no Google Cloud: Origin http://127.0.0.1:5000 e Redirect {expected_redirect}', 'info')
        except Exception:
            pass
        return redirect(url_for('login'))

    if not google.authorized:
        return redirect(url_for('google.login'))
    
    resp = google.get('/oauth2/v2/userinfo')
    if resp.ok:
        user_info = resp.json()
        email = user_info['email']
        
        # Verificar se o usuário já existe
        user = User.query.filter_by(email=email).first()
        
        if not user:
            # Criar novo usuário como restaurante
            user = User(
                name=user_info['name'],
                email=email,
                social_id=user_info['id'],
                social_provider='google',
                password=None,  # Sem senha para login social
                is_restaurant=True
            )
            db.session.add(user)
            db.session.commit()
        else:
            # Bloquear login social para contas que não são restaurante
            if not user.is_restaurant:
                flash('Login social é exclusivo para contas de restaurante.', 'warning')
                return redirect(url_for('login'))
        
        login_user(user)
        
        # Redirecionar automaticamente para criar restaurante se não houver um cadastrado
        if user.is_restaurant:
            has_restaurant = Restaurant.query.filter_by(owner_id=user.id).first()
            if not has_restaurant:
                flash('Login com Google realizado! Agora cadastre seu restaurante.', 'info')
                return redirect(url_for('create_restaurant'))
        
        flash('Login com Google realizado com sucesso!', 'success')
        return redirect(url_for('index'))
    
    # Em desenvolvimento, exibir detalhes para diagnóstico
    try:
        error_text = resp.text if hasattr(resp, 'text') else str(resp)
        flash(f'Falha ao fazer login com Google. Código: {getattr(resp, "status_code", "?")}. Detalhes: {error_text}', 'danger')
    except Exception:
        flash('Falha ao fazer login com Google.', 'danger')
    return redirect(url_for('login'))

@app.route('/login/facebook')
def facebook_login():
    # Verificação preventiva: credenciais do Facebook configuradas?
    client_id = app.config.get('FACEBOOK_OAUTH_CLIENT_ID')
    client_secret = app.config.get('FACEBOOK_OAUTH_CLIENT_SECRET')
    placeholders = {'seu-app-id-aqui', 'seu-app-secret-aqui', None, ''}
    if client_id in placeholders or client_secret in placeholders:
        flash('Credenciais do Facebook não configuradas. Atualize o arquivo .env com seu App ID e App Secret e reinicie o servidor.', 'danger')
        try:
            expected_redirect = url_for('facebook.authorized', _external=True)
            flash(f'URI de Redirect esperada no Facebook: {expected_redirect}', 'info')
        except Exception:
            pass
        return redirect(url_for('login'))
    if not facebook.authorized:
        return redirect(url_for('facebook.login'))
    
    resp = facebook.get('/me?fields=id,name,email')
    if resp.ok:
        user_info = resp.json()
        email = user_info.get('email')
        
        if not email:
            flash('Não foi possível obter o email do Facebook.', 'danger')
            return redirect(url_for('login'))
        
        # Verificar se o usuário já existe
        user = User.query.filter_by(email=email).first()
        
        if not user:
            # Criar novo usuário como restaurante
            user = User(
                name=user_info['name'],
                email=email,
                social_id=user_info['id'],
                social_provider='facebook',
                password=None,  # Sem senha para login social
                is_restaurant=True
            )
            db.session.add(user)
            db.session.commit()
        else:
            # Bloquear login social para contas que não são restaurante
            if not user.is_restaurant:
                flash('Login social é exclusivo para contas de restaurante.', 'warning')
                return redirect(url_for('login'))
        
        login_user(user)
        
        # Redirecionar automaticamente para criar restaurante se não houver um cadastrado
        if user.is_restaurant:
            has_restaurant = Restaurant.query.filter_by(owner_id=user.id).first()
            if not has_restaurant:
                flash('Login com Facebook realizado! Agora cadastre seu restaurante.', 'info')
                return redirect(url_for('create_restaurant'))
        
        flash('Login com Facebook realizado com sucesso!', 'success')
        return redirect(url_for('index'))
    
    try:
        error_text = resp.text if hasattr(resp, 'text') else str(resp)
        flash(f'Falha ao fazer login com Facebook. Código: {getattr(resp, "status_code", "?")}. Detalhes: {error_text}', 'danger')
    except Exception:
        flash('Falha ao fazer login com Facebook.', 'danger')
    return redirect(url_for('login'))

@app.route('/restaurant/<int:restaurant_id>')
def restaurant(restaurant_id):
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    menu_items = MenuItem.query.filter_by(restaurant_id=restaurant_id).all()
    return render_template('restaurant.html', restaurant=restaurant, menu_items=menu_items)

@app.route('/cart', methods=['GET'])
@login_required
def cart():
    return render_template('cart.html')

@app.route('/add_to_cart', methods=['POST'])
@login_required
def add_to_cart():
    data = request.json
    item_id = data.get('item_id')
    quantity = data.get('quantity', 1)
    
    # Lógica para adicionar ao carrinho (usando sessão ou banco de dados)
    # Aqui usaremos JavaScript para gerenciar o carrinho no lado do cliente
    
    return jsonify({'success': True})

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    if request.method == 'POST':
        # Processar o pedido
        data = request.json
        items = data.get('items')
        restaurant_id = data.get('restaurant_id')
        total = data.get('total')
        
        new_order = Order(
            user_id=current_user.id,
            restaurant_id=restaurant_id,
            total=total,
            delivery_address=current_user.address
        )
        
        db.session.add(new_order)
        db.session.commit()
        
        for item in items:
            order_item = OrderItem(
                order_id=new_order.id,
                menu_item_id=item['id'],
                quantity=item['quantity'],
                price=item['price']
            )
            db.session.add(order_item)
        
        db.session.commit()
        
        return jsonify({'success': True, 'order_id': new_order.id})
    
    return render_template('checkout.html')

@app.route('/orders')
@login_required
def orders():
    user_orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template('orders.html', orders=user_orders)

@app.route('/orders/<int:order_id>/cancel', methods=['POST'])
@login_required
def cancel_order(order_id):
    order = Order.query.get_or_404(order_id)
    # Permitir cancelamento apenas pelo dono do pedido ou admin
    if order.user_id != current_user.id and not current_user.is_admin:
        flash('Você não tem permissão para cancelar este pedido.', 'danger')
        return redirect(url_for('orders'))
    # Apenas pedidos pendentes podem ser cancelados
    if order.status != 'pending':
        flash('Apenas pedidos pendentes podem ser cancelados.', 'warning')
        return redirect(url_for('orders'))
    order.status = 'cancelled'
    db.session.commit()
    flash(f'Pedido #{order.id} foi cancelado.', 'success')
    return redirect(url_for('orders'))

# Acompanhamento de pedidos por restaurante (owner/admin)
@app.route('/restaurant/<int:restaurant_id>/orders')
@login_required
def restaurant_orders(restaurant_id):
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    if restaurant.owner_id != current_user.id and not current_user.is_admin:
        flash('Você não tem permissão para ver os pedidos deste restaurante.', 'danger')
        return redirect(url_for('index'))
    orders = Order.query.filter_by(restaurant_id=restaurant_id).order_by(Order.created_at.desc()).all()
    statuses = ['pending', 'preparing', 'delivering', 'delivered', 'cancelled']
    return render_template('restaurant_orders.html', restaurant=restaurant, orders=orders, statuses=statuses)

# Atualização de status do pedido (owner/admin)
@app.route('/orders/<int:order_id>/status', methods=['POST'])
@login_required
def update_order_status(order_id):
    order = Order.query.get_or_404(order_id)
    restaurant = Restaurant.query.get(order.restaurant_id)
    if not restaurant or (restaurant.owner_id != current_user.id and not current_user.is_admin):
        flash('Você não tem permissão para atualizar o status deste pedido.', 'danger')
        return redirect(url_for('orders'))
    new_status = request.form.get('status')
    allowed_statuses = ['pending', 'preparing', 'delivering', 'delivered', 'cancelled']
    if new_status not in allowed_statuses:
        flash('Status inválido.', 'warning')
        return redirect(url_for('restaurant_orders', restaurant_id=order.restaurant_id))
    # Regras de transição
    sequence = ['pending', 'preparing', 'delivering', 'delivered']
    current = order.status
    if new_status == current:
        pass
    elif new_status == 'cancelled':
        if current != 'pending':
            flash('Só é possível cancelar pedidos pendentes.', 'warning')
            return redirect(url_for('restaurant_orders', restaurant_id=order.restaurant_id))
    else:
        try:
            ci = sequence.index(current)
            ni = sequence.index(new_status)
        except ValueError:
            flash('Transição de status não permitida.', 'warning')
            return redirect(url_for('restaurant_orders', restaurant_id=order.restaurant_id))
        if ni != ci + 1:
            flash('Transição de status não permitida.', 'warning')
            return redirect(url_for('restaurant_orders', restaurant_id=order.restaurant_id))
    order.status = new_status
    db.session.commit()
    flash(f'Status do pedido #{order.id} atualizado para {new_status}.', 'success')
    next_url = request.form.get('next') or url_for('restaurant_orders', restaurant_id=order.restaurant_id)
    return redirect(next_url)

# CRUD de Restaurantes
@app.route('/restaurants')
@login_required
def list_restaurants():
    q = request.args.get('q', '').strip()
    if q:
        restaurants = Restaurant.query.filter(
            (Restaurant.name.ilike(f'%{q}%')) |
            (Restaurant.category.ilike(f'%{q}%')) |
            (Restaurant.address.ilike(f'%{q}%'))
        ).all()
    else:
        restaurants = Restaurant.query.all()
    return render_template('restaurants.html', restaurants=restaurants, q=q)

@app.route('/restaurants/new', methods=['GET', 'POST'])
@login_required
def create_restaurant():
    if not current_user.is_restaurant:
        current_user.is_restaurant = True
        db.session.commit()
        flash('Sua conta foi convertida para restaurante. Preencha os dados do seu restaurante.', 'info')
        
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        address = request.form.get('address')
        phone = request.form.get('phone')
        image_url = request.form.get('image_url')
        category = request.form.get('category')
        
        restaurant = Restaurant(
            name=name,
            description=description,
            address=address,
            phone=phone,
            image_url=image_url,
            category=category,
            owner_id=current_user.id
        )
        
        db.session.add(restaurant)
        db.session.commit()
        
        flash('Restaurante criado com sucesso!', 'success')
        return redirect(url_for('list_restaurants'))
        
    return render_template('restaurant_form.html')

@app.route('/restaurants/<int:restaurant_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_restaurant(restaurant_id):
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    
    # Verificar se o usuário é o proprietário
    if restaurant.owner_id != current_user.id and not current_user.is_admin:
        flash('Você não tem permissão para editar este restaurante.', 'danger')
        return redirect(url_for('list_restaurants'))
    
    if request.method == 'POST':
        # Atualiza somente os campos presentes no formulário para evitar sobrescrever com None
        if 'name' in request.form:
            restaurant.name = request.form.get('name')
        if 'description' in request.form:
            restaurant.description = request.form.get('description')
        if 'address' in request.form:
            restaurant.address = request.form.get('address')
        if 'phone' in request.form:
            restaurant.phone = request.form.get('phone')
        if 'image_url' in request.form:
            restaurant.image_url = request.form.get('image_url')
        if 'category' in request.form:
            restaurant.category = request.form.get('category')
        # Campos adicionais usados na tabela e modal
        if 'delivery_fee' in request.form:
            try:
                restaurant.delivery_fee = float(request.form.get('delivery_fee'))
            except (TypeError, ValueError):
                pass
        if 'delivery_time' in request.form:
            try:
                restaurant.delivery_time = int(request.form.get('delivery_time'))
            except (TypeError, ValueError):
                pass
        if 'logo' in request.form:
            restaurant.logo = request.form.get('logo')
        
        db.session.commit()
        
        flash('Restaurante atualizado com sucesso!', 'success')
        return redirect(url_for('list_restaurants'))
        
    return render_template('restaurant_form.html', restaurant=restaurant)

@app.route('/restaurants/<int:restaurant_id>/delete', methods=['POST'])
@login_required
def delete_restaurant(restaurant_id):
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    
    # Verificar se o usuário é o proprietário
    if restaurant.owner_id != current_user.id and not current_user.is_admin:
        flash('Você não tem permissão para excluir este restaurante.', 'danger')
        return redirect(url_for('list_restaurants'))
    
    # Excluir todos os itens do menu associados
    MenuItem.query.filter_by(restaurant_id=restaurant.id).delete()
    
    # Excluir o restaurante
    db.session.delete(restaurant)
    db.session.commit()
    
    flash('Restaurante excluído com sucesso!', 'success')
    return redirect(url_for('list_restaurants'))

# CRUD de Refeições/Lanches
@app.route('/restaurants/<int:restaurant_id>/menu')
@login_required
def list_menu_items(restaurant_id):
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    menu_items = MenuItem.query.filter_by(restaurant_id=restaurant_id).all()
    return render_template('menu_items.html', restaurant=restaurant, menu_items=menu_items)

@app.route('/restaurants/<int:restaurant_id>/menu/new', methods=['GET', 'POST'])
@login_required
def create_menu_item(restaurant_id):
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    
    # Verificar se o usuário é o proprietário do restaurante
    if restaurant.owner_id != current_user.id and not current_user.is_admin:
        flash('Você não tem permissão para adicionar itens a este restaurante.', 'danger')
        return redirect(url_for('list_menu_items', restaurant_id=restaurant_id))
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        price = float(request.form.get('price'))
        image_url = request.form.get('image_url')
        category = request.form.get('category')
        
        menu_item = MenuItem(
            name=name,
            description=description,
            price=price,
            image_url=image_url,
            category=category,
            restaurant_id=restaurant_id
        )
        
        db.session.add(menu_item)
        db.session.commit()
        
        flash('Item adicionado com sucesso!', 'success')
        return redirect(url_for('list_menu_items', restaurant_id=restaurant_id))
        
    return render_template('menu_item_form.html', restaurant=restaurant)

@app.route('/menu-items/<int:item_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_menu_item(item_id):
    menu_item = MenuItem.query.get_or_404(item_id)
    restaurant = Restaurant.query.get_or_404(menu_item.restaurant_id)
    
    # Verificar se o usuário é o proprietário do restaurante
    if restaurant.owner_id != current_user.id and not current_user.is_admin:
        flash('Você não tem permissão para editar itens deste restaurante.', 'danger')
        return redirect(url_for('list_menu_items', restaurant_id=restaurant.id))
    
    if request.method == 'POST':
        menu_item.name = request.form.get('name')
        menu_item.description = request.form.get('description')
        menu_item.price = float(request.form.get('price'))
        menu_item.image_url = request.form.get('image_url')
        menu_item.category = request.form.get('category')
        
        db.session.commit()
        
        flash('Item atualizado com sucesso!', 'success')
        return redirect(url_for('list_menu_items', restaurant_id=restaurant.id))
        
    return render_template('menu_item_form.html', restaurant=restaurant, menu_item=menu_item)

@app.route('/menu-items/<int:item_id>/delete', methods=['POST'])
@login_required
def delete_menu_item(item_id):
    menu_item = MenuItem.query.get_or_404(item_id)
    restaurant = Restaurant.query.get_or_404(menu_item.restaurant_id)
    
    # Verificar se o usuário é o proprietário do restaurante
    if restaurant.owner_id != current_user.id and not current_user.is_admin:
        flash('Você não tem permissão para excluir itens deste restaurante.', 'danger')
        return redirect(url_for('list_menu_items', restaurant_id=restaurant.id))
    
    db.session.delete(menu_item)
    db.session.commit()
    
    flash('Item excluído com sucesso!', 'success')
    return redirect(url_for('list_menu_items', restaurant_id=restaurant.id))

# CRUD de Usuários
@app.route('/users')
@login_required
def list_users():
    if not current_user.is_restaurant:  # Apenas administradores podem ver todos os usuários
        return redirect(url_for('index'))
    users = User.query.all()
    return render_template('users.html', users=users)

@app.route('/users/<int:user_id>')
@login_required
def view_user(user_id):
    if current_user.id != user_id and not current_user.is_restaurant:
        return redirect(url_for('index'))
    user = User.query.get_or_404(user_id)
    return render_template('user_detail.html', user=user)

@app.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    if current_user.id != user_id and not current_user.is_restaurant:
        return redirect(url_for('index'))
    
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        user.name = request.form.get('name')
        user.email = request.form.get('email')
        user.address = request.form.get('address')
        user.phone = request.form.get('phone')
        
        if request.form.get('password'):
            user.password = generate_password_hash(request.form.get('password'), method='pbkdf2:sha256')
        
        db.session.commit()
        flash('Usuário atualizado com sucesso!')
        return redirect(url_for('view_user', user_id=user.id))
    
    return render_template('edit_user.html', user=user)

@app.route('/users/delete/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if current_user.id != user_id and not current_user.is_restaurant:
        return redirect(url_for('index'))
    
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    
    if current_user.id == user_id:
        logout_user()
        flash('Sua conta foi excluída com sucesso!')
        return redirect(url_for('index'))
    
    flash('Usuário excluído com sucesso!')
    return redirect(url_for('list_users'))

# Inicialização do banco de dados
with app.app_context():
    # Cria as tabelas conforme os modelos definidos acima (se o arquivo do banco não existir)
    db.create_all()
    # Seed de dados de demonstração para facilitar testes em uma instalação limpa
    # Só executa quando não há usuários nem restaurantes, evitando duplicar registros
    if User.query.count() == 0 and Restaurant.query.count() == 0:
        demo_user = User(
            name='Demo Restaurante',
            email='demo@restaurant.com',
            password=generate_password_hash('123456', method='pbkdf2:sha256'),
            address='Rua Exemplo, 123',
            phone='(11) 99999-9999',
            is_restaurant=True
        )
        db.session.add(demo_user)
        db.session.commit()

        demo_restaurant = Restaurant(
            owner_id=demo_user.id,
            name='Pizzaria Demo',
            description='A melhor pizza da cidade',
            category='Italiana',
            delivery_fee=5.99,
            delivery_time=30,
            rating=4.5,
            logo=None,
            address='Rua Pizza, 456',
            phone='(11) 88888-8888',
            image_url='https://via.placeholder.com/600x300'
        )
        db.session.add(demo_restaurant)
        db.session.commit()

        demo_item = MenuItem(
            restaurant_id=demo_restaurant.id,
            name='Pizza Margherita',
            description='Clássica com tomate, mozzarella e manjericão',
            price=39.90,
            image_url='https://via.placeholder.com/300',
            category='Pizza',
            available=True
        )
        db.session.add(demo_item)
        db.session.commit()

# Rota de diagnóstico para verificar persistência e caminho do banco
@app.route('/debug/db-info')
def debug_db_info():
    uri = app.config.get('SQLALCHEMY_DATABASE_URI')
    try:
        database = db.engine.url.database
    except Exception:
        database = None
    if database and not os.path.isabs(database):
        db_path = os.path.abspath(database)
    else:
        db_path = database

# Ferramentas para apresentação: resetar banco e popular dados demo
@app.route('/debug/reset-db', methods=['POST'])
def debug_reset_db():
    db_path = db.engine.url.database
    # Tenta remover arquivo atual de banco
    if db_path and os.path.exists(db_path):
        try:
            os.remove(db_path)
        except Exception:
            pass
    # Recria o esquema
    db.create_all()
    return jsonify({'status': 'ok', 'message': 'Banco resetado e recriado.'})

@app.route('/debug/seed-demo', methods=['POST'])
def debug_seed_demo():
    if User.query.count() == 0 and Restaurant.query.count() == 0:
        demo_user = User(
            name='Demo Restaurante',
            email='demo@restaurant.com',
            password=generate_password_hash('123456', method='pbkdf2:sha256'),
            address='Rua Exemplo, 123',
            phone='(11) 99999-9999',
            is_restaurant=True
        )
        db.session.add(demo_user)
        db.session.commit()

        demo_restaurant = Restaurant(
            owner_id=demo_user.id,
            name='Pizzaria Demo',
            description='A melhor pizza da cidade',
            category='Italiana',
            delivery_fee=5.99,
            delivery_time=30,
            rating=4.5,
            logo=None,
            address='Rua Pizza, 456',
            phone='(11) 88888-8888',
            image_url='https://via.placeholder.com/600x300'
        )
        db.session.add(demo_restaurant)
        db.session.commit()

        demo_item = MenuItem(
            restaurant_id=demo_restaurant.id,
            name='Pizza Margherita',
            description='Clássica com tomate, mozzarella e manjericão',
            price=39.90,
            image_url='https://via.placeholder.com/300',
            category='Pizza',
            available=True
        )
        db.session.add(demo_item)
        db.session.commit()
        created = True
    else:
        created = False
    return jsonify({'status': 'ok', 'seeded': created})
    counts = {
        'users': User.query.count(),
        'restaurants': Restaurant.query.count(),
        'menu_items': MenuItem.query.count(),
        'orders': Order.query.count(),
        'order_items': OrderItem.query.count()
    }
    return jsonify({'uri': uri, 'db_path': db_path, 'counts': counts})

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=int(os.environ.get('PORT', 5000)), debug=True, use_reloader=False)