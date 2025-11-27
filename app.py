from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime, timedelta
try:
    from flask_dance.contrib.google import make_google_blueprint, google
    from flask_dance.contrib.facebook import make_facebook_blueprint, facebook
    from flask_dance.consumer.storage.sqla import OAuthConsumerMixin, SQLAlchemyStorage
    from flask_dance.consumer import oauth_authorized
    OAUTH_AVAILABLE = True
except ImportError:
    OAUTH_AVAILABLE = False
    make_google_blueprint = None
    make_facebook_blueprint = None
    google = None
    facebook = None
    SQLAlchemyStorage = None
    oauth_authorized = None
from sqlalchemy.orm.exc import NoResultFound
from dotenv import load_dotenv
import smtplib
import ssl
from email.message import EmailMessage
from email.mime.text import MIMEText
import requests
import random
import string
from flask_mail import Mail, Message
import math
import json
from oauthlib.oauth2.rfc6749.errors import MismatchingStateError

# Carrega variáveis do .env e permite HTTP em desenvolvimento
load_dotenv()
os.environ.setdefault('OAUTHLIB_INSECURE_TRANSPORT', '1')

# Configuração da aplicação
# Configuração principal do Flask
app = Flask(__name__)
# Chave secreta para proteger sessões e CSRF em formulários
app.config['SECRET_KEY'] = 'food-delivery-secret-key'
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = False
# Banco de dados SQLite no arquivo food_delivery.db (na raiz do projeto)
# Dica: se preferir, mude para dentro de instance com: 'sqlite:///instance/food_delivery.db'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cliente.db'
app.config['SQLALCHEMY_BINDS'] = {
    'restaurants': 'sqlite:///restaurante.db'
}
# Desativa rastreamento de modificações (melhora performance)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configuração de email (Flask-Mail)
# Usa variáveis de ambiente se disponíveis; caso contrário, aplica defaults (Gmail) como solicitado
if os.environ.get('MAIL_SERVER') or os.environ.get('SMTP_HOST'):
    app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER') or os.environ.get('SMTP_HOST')
    app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT') or os.environ.get('SMTP_PORT') or '587')
    # Determina SSL/TLS a partir das variáveis
    secure = (os.environ.get('SMTP_SECURE') or '').lower()
    use_ssl_env = (os.environ.get('MAIL_USE_SSL') or '').lower() in ('1','true','yes') or secure == 'ssl' or app.config['MAIL_PORT'] == 465
    app.config['MAIL_USE_SSL'] = use_ssl_env
    app.config['MAIL_USE_TLS'] = not use_ssl_env
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME') or os.environ.get('SMTP_USER')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD') or os.environ.get('SMTP_PASSWORD') or os.environ.get('SMTP_PASS')
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER') or os.environ.get('SMTP_FROM') or os.environ.get('MAIL_FROM') or app.config['MAIL_USERNAME']
else:
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USE_SSL'] = False
    app.config['MAIL_USERNAME'] = 'seuemail@gmail.com'  # substitua pelo seu email
    app.config['MAIL_PASSWORD'] = 'sua_senha_de_app'    # substitua pela sua app password
    app.config['MAIL_DEFAULT_SENDER'] = 'seuemail@gmail.com'

mail = Mail(app)

# Modo desenvolvimento: exibir código na tela quando email/SMS não estiverem configurados
app.config['SHOW_DEV_CODE'] = (
    (not os.environ.get('MAIL_USERNAME') and not os.environ.get('SMTP_USER')) or
    (app.config.get('MAIL_USERNAME') in ('seuemail@gmail.com', None, ''))
)
app.config['ALLOW_OPEN_ACCESS'] = False

verification_codes = {}

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

# Geocodificação e cálculo de distância (Haversine)
def geocode_address(query: str):
    """Obtém (lat, lon) via Nominatim para um endereço no Brasil."""
    try:
        if not query:
            return None
        url = "https://nominatim.openstreetmap.org/search"
        params = {"format": "json", "q": query, "countrycodes": "br"}
        headers = {"User-Agent": "FoodDeliveryApp/1.0 (contato: dev@example.com)"}
        resp = requests.get(url, params=params, headers=headers, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list) and data:
                lat = float(data[0].get("lat"))
                lon = float(data[0].get("lon"))
                return (lat, lon)
    except Exception:
        pass
    return None

def reverse_geocode(lat: float, lon: float):
    try:
        if lat is None or lon is None:
            return None
        url = "https://nominatim.openstreetmap.org/reverse"
        params = {"format": "json", "lat": str(lat), "lon": str(lon), "addressdetails": "1"}
        headers = {"User-Agent": "FoodDeliveryApp/1.0 (contato: dev@example.com)"}
        resp = requests.get(url, params=params, headers=headers, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            addr = data.get("address", {}) if isinstance(data, dict) else {}
            street = addr.get("road") or addr.get("pedestrian") or addr.get("footway") or addr.get("residential") or addr.get("neighbourhood")
            number = addr.get("house_number")
            neighborhood = addr.get("neighbourhood") or addr.get("suburb") or addr.get("city_district")
            city = addr.get("city") or addr.get("town") or addr.get("village") or addr.get("municipality")
            state = addr.get("state") or addr.get("region")
            zip_code = addr.get("postcode")
            return {
                "street": street or "",
                "number": number or "",
                "neighborhood": neighborhood or "",
                "city": city or "",
                "state": state or "SP",
                "zip_code": zip_code or ""
            }
    except Exception:
        pass
    return None

@app.route('/api/reverse-geocode')
def api_reverse_geocode():
    try:
        lat = parse_float(request.args.get('lat'))
        lon = parse_float(request.args.get('lon'))
        data = reverse_geocode(lat, lon)
        if not data:
            data = {"street": "", "number": "", "neighborhood": "", "city": "São Paulo", "state": "SP", "zip_code": ""}
        return jsonify({"ok": True, "address": data})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400

@app.route('/api/viacep')
def api_viacep():
    try:
        cep_raw = request.args.get('cep') or ''
        cep = ''.join(ch for ch in str(cep_raw) if ch.isdigit())
        if len(cep) != 8:
            return jsonify({'ok': False, 'error': 'CEP inválido'}), 400
        url = f'https://viacep.com.br/ws/{cep}/json/'
        resp = requests.get(url, timeout=8)
        if resp.status_code != 200:
            return jsonify({'ok': False, 'error': 'Falha ao consultar CEP'}), 400
        data = resp.json()
        if isinstance(data, dict) and data.get('erro'):
            return jsonify({'ok': False, 'error': 'CEP não encontrado'}), 404
        address = {
            'street': (data.get('logradouro') or ''),
            'number': '',
            'neighborhood': (data.get('bairro') or ''),
            'city': (data.get('localidade') or ''),
            'state': (data.get('uf') or ''),
            'zip_code': (f"{cep[:5]}-{cep[5:]}" if cep else ''),
            'complement': (data.get('complemento') or '')
        }
        return jsonify({'ok': True, 'address': address})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400

@app.route('/api/set-user-location', methods=['POST', 'GET'])
def api_set_user_location():
    try:
        if request.method == 'GET':
            src = request.args
        else:
            data = request.get_json(silent=True)
            if isinstance(data, dict) and data:
                src = data
            else:
                src = request.form or {}
                if not src:
                    raw_text = request.get_data(as_text=True) or ''
                    try:
                        maybe = json.loads(raw_text)
                        if isinstance(maybe, dict):
                            src = maybe
                    except Exception:
                        pass
                    if not src and raw_text:
                        try:
                            pairs = dict(part.split('=') for part in raw_text.split('&') if '=' in part)
                            src = pairs
                        except Exception:
                            src = {}
        def pick(*keys):
            for k in keys:
                v = src.get(k)
                if v is not None:
                    return v
            return None
        lat_raw = pick('lat', 'latitude', 'user_lat')
        lon_raw = pick('lon', 'longitude', 'user_lon')
        acc_raw = pick('accuracy', 'user_accuracy', 'acc')
        lat = parse_float(lat_raw)
        lon = parse_float(lon_raw)
        if lat is None or lon is None:
            return jsonify({'ok': False, 'error': 'Coordenadas inválidas'}), 400
        session['user_lat'] = lat
        session['user_lon'] = lon
        acc = parse_float(acc_raw)
        if acc is not None:
            session['user_accuracy'] = acc
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distância aproximada (km) entre dois pontos geográficos."""
    R = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# Utilitários de parse numérico
def parse_float(s):
    if not s:
        return None
    try:
        return float(str(s).replace(',', '.'))
    except (ValueError, TypeError):
        return None

def parse_int(s):
    if not s:
        return None
    try:
        return int(s)
    except (ValueError, TypeError):
        return None

# Validação de pagamento (simulada/sandbox)
def validate_payment(method: str, total: float) -> bool:
    """
    Simula validação de pagamento. Em sandbox, considera aprovado
    para métodos conhecidos e valores > 0.
    """
    try:
        method = (method or '').strip().lower()
        if total is None or total <= 0:
            return False
        if method in ('credit_card', 'debit_card', 'pix', 'cash'):
            return True
    except Exception:
        pass
    return False

def get_restaurant_coords(restaurant):
    try:
        if not restaurant or not restaurant.address:
            return None
        rec = RestaurantGeo.query.filter_by(restaurant_id=restaurant.id).first()
        if rec:
            return (rec.lat, rec.lon)
        coords = geocode_address(restaurant.address)
        if coords:
            lat, lon = coords
            try:
                rec = RestaurantGeo(restaurant_id=restaurant.id, lat=lat, lon=lon)
                db.session.add(rec)
                db.session.commit()
            except Exception:
                db.session.rollback()
            return coords
    except Exception:
        pass
    return None

# Configuração dos blueprints OAuth
if OAUTH_AVAILABLE:
    google_bp = make_google_blueprint(
        client_id=app.config['GOOGLE_OAUTH_CLIENT_ID'],
        client_secret=app.config['GOOGLE_OAUTH_CLIENT_SECRET'],
        scope=["https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile", "openid"],
        redirect_to="google_login"
    )
    try:
        google_bp.authorization_url_params = {"prompt": "consent select_account", "access_type": "offline", "include_granted_scopes": "true"}
    except Exception:
        pass
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
if OAUTH_AVAILABLE:
    try:
        google_bp.storage = SQLAlchemyStorage(OAuth, db.session, user=current_user, user_required=False)
    except NameError:
        pass

# Modelos do banco de dados
# User: representa um usuário do sistema (cliente ou dono de restaurante). Suporta login social.
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column('nome', db.String(100), nullable=False)
    email = db.Column('email', db.String(100), unique=True, nullable=True)
    password = db.Column('senha', db.String(200), nullable=True)  # Nullable para permitir login social
    address = db.Column('endereco', db.String(200))
    phone = db.Column('telefone', db.String(20))
    is_restaurant = db.Column('eh_restaurante', db.Boolean, default=False)
    is_admin = db.Column('eh_admin', db.Boolean, default=False)
    # Relacionamentos com pedidos agora são resolvidos por consulta cruzando binds
    
    # Campos para autenticação social
    social_id = db.Column('id_social', db.String(100), unique=True, nullable=True)
    social_provider = db.Column('provedor_social', db.String(20), nullable=True)
    
    # Campos para código de verificação de 6 dígitos
    verification_code = db.Column('codigo_verificacao', db.String(6), nullable=True)
    verification_code_expires = db.Column('codigo_verificacao_expira_em', db.DateTime, nullable=True)
    is_verified = db.Column('verificado', db.Boolean, default=False)
    
    def __repr__(self):
        return f'<User {self.name}>'

if OAUTH_AVAILABLE:
    class OAuth(OAuthConsumerMixin, db.Model):
        user_id = db.Column(db.Integer, db.ForeignKey(User.id))
        user = db.relationship(User)
else:
    class OAuth(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey(User.id))
        user = db.relationship(User)

# Configura storage do Google com SQLAlchemy assim que OAuth está disponível
if OAUTH_AVAILABLE:
    try:
        google_bp.storage = SQLAlchemyStorage(OAuth, db.session, user=current_user, user_required=False)
    except Exception:
        pass

# Restaurant: restaurante pertence a um usuário (owner_id) e possui itens de menu
class Restaurant(db.Model):
    __bind_key__ = 'restaurants'
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column('id_dono', db.Integer, nullable=False)
    name = db.Column('nome', db.String(100), nullable=False)
    description = db.Column('descricao', db.Text)
    category = db.Column('categoria', db.String(50))
    delivery_fee = db.Column('taxa_entrega', db.Float, default=0.0)
    delivery_time = db.Column('tempo_entrega', db.Integer)  # em minutos
    rating = db.Column('avaliacao', db.Float, default=0.0)
    logo = db.Column('logo', db.String(200))
    address = db.Column('endereco', db.String(200), nullable=False)
    phone = db.Column('telefone', db.String(20))
    image_url = db.Column('url_imagem', db.String(200))
    items = db.relationship('MenuItem', backref='restaurant', lazy=True)
    
    def __repr__(self):
        return f'<Restaurant {self.name}>'

# MenuItem: item do cardápio vinculado ao restaurante; pode ter image_url
class MenuItem(db.Model):
    __bind_key__ = 'restaurants'
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column('restaurante_id', db.Integer, db.ForeignKey('restaurant.id'), nullable=False)
    name = db.Column('nome', db.String(100), nullable=False)
    description = db.Column('descricao', db.Text)
    price = db.Column('preco', db.Float, nullable=False)
    image = db.Column('imagem', db.String(200))
    image_url = db.Column('url_imagem', db.String(200))
    category = db.Column('categoria', db.String(50))
    available = db.Column('disponivel', db.Boolean, default=True)
    
    def __repr__(self):
        return f'<MenuItem {self.name}>'

# Cart: carrinho de compras do usuário
class Cart(db.Model):
    __tablename__ = 'cart'
    __bind_key__ = 'restaurants'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column('usuario_id', db.Integer, nullable=False)
    restaurant_id = db.Column('restaurante_id', db.Integer, db.ForeignKey('restaurant.id'), nullable=False)
    created_at = db.Column('criado_em', db.DateTime, default=datetime.utcnow)
    updated_at = db.Column('atualizado_em', db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    items = db.relationship('CartItem', backref='cart', lazy=True, cascade='all, delete-orphan')
    
    restaurant = db.relationship('Restaurant', backref=db.backref('carts', lazy=True))
    
    def get_total(self):
        return sum(item.get_subtotal() for item in self.items)
    
    def get_item_count(self):
        return sum(item.quantity for item in self.items)
    
    def __repr__(self):
        return f'<Cart {self.id} - User {self.user_id}>'

# CartItem: item no carrinho
class CartItem(db.Model):
    __bind_key__ = 'restaurants'
    __tablename__ = 'cart_item'
    id = db.Column(db.Integer, primary_key=True)
    cart_id = db.Column('carrinho_id', db.Integer, db.ForeignKey('cart.id'), nullable=False)
    menu_item_id = db.Column('item_menu_id', db.Integer, db.ForeignKey('menu_item.id'), nullable=False)
    quantity = db.Column('quantidade', db.Integer, nullable=False, default=1)
    price = db.Column('preco', db.Float, nullable=False)  # Preço no momento da adição
    
    menu_item = db.relationship('MenuItem', backref='cart_items')
    
    def get_subtotal(self):
        return self.quantity * self.price
    
    def __repr__(self):
        return f'<CartItem {self.menu_item.name} x{self.quantity}>'

class RestaurantGeo(db.Model):
    __bind_key__ = 'restaurants'
    __tablename__ = 'restaurant_geo'
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurant.id'), unique=True, nullable=False)
    lat = db.Column(db.Float, nullable=False)
    lon = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    restaurant = db.relationship('Restaurant', backref=db.backref('geo_record', uselist=False))

# Order: pedido com status, total e endereço; criado em created_at e possui itens (OrderItem)
class UserAddress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column('usuario_id', db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column('nome', db.String(100), nullable=False)  # Ex: "Casa", "Trabalho", "Apartamento"
    street = db.Column('rua', db.String(200), nullable=False)
    number = db.Column('numero', db.String(20), nullable=False)
    complement = db.Column('complemento', db.String(100))  # Apartamento, bloco, etc.
    neighborhood = db.Column('bairro', db.String(100), nullable=False)
    city = db.Column('cidade', db.String(100), nullable=False)
    state = db.Column('estado', db.String(50), nullable=False)
    zip_code = db.Column('cep', db.String(20), nullable=False)
    reference = db.Column('referencia', db.String(200))  # Ponto de referência
    is_default = db.Column('padrao', db.Boolean, default=False)
    created_at = db.Column('criado_em', db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('addresses', lazy=True))
    
    def __repr__(self):
        return f'<UserAddress {self.name} - {self.user.name}>'
    
    def get_full_address(self):
        """Retorna o endereço completo formatado"""
        address_parts = [
            f"{self.street}, {self.number}",
            self.complement,
            self.neighborhood,
            f"{self.city} - {self.state}",
            f"CEP: {self.zip_code}"
        ]
        return ", ".join([part for part in address_parts if part])

class Order(db.Model):
    __bind_key__ = 'restaurants'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column('usuario_id', db.Integer, nullable=False)
    restaurant_id = db.Column('restaurante_id', db.Integer, db.ForeignKey('restaurant.id'), nullable=False)
    address_id = db.Column('endereco_id', db.Integer, nullable=False)
    status = db.Column('status', db.String(20), default='pending')  # pending, confirmed, preparing, ready, delivering, delivered, cancelled
    subtotal = db.Column('subtotal', db.Float, nullable=False)
    delivery_fee = db.Column('taxa_entrega', db.Float, nullable=False, default=0.0)
    total = db.Column('total', db.Float, nullable=False)
    payment_method = db.Column('metodo_pagamento', db.String(50), nullable=False)  # credit_card, debit_card, pix, cash
    notes = db.Column('observacoes', db.Text)  # Observações do pedido
    created_at = db.Column('criado_em', db.DateTime, default=datetime.utcnow)
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')
    
    restaurant = db.relationship('Restaurant', backref=db.backref('restaurant_orders', lazy=True))
    
    def get_status_display(self):
        status_map = {
            'pending': 'Pendente',
            'confirmed': 'Confirmado',
            'preparing': 'Preparando',
            'ready': 'Pronto',
            'delivering': 'Saiu para entrega',
            'delivered': 'Entregue',
            'cancelled': 'Cancelado'
        }
        return status_map.get(self.status, self.status)
    
    def __repr__(self):
        return f'<Order {self.id} - {self.status}>'

class OrderItem(db.Model):
    __bind_key__ = 'restaurants'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column('pedido_id', db.Integer, db.ForeignKey('order.id'), nullable=False)
    menu_item_id = db.Column('item_menu_id', db.Integer, db.ForeignKey('menu_item.id'), nullable=False)
    quantity = db.Column('quantidade', db.Integer, nullable=False)
    price = db.Column('preco', db.Float, nullable=False)
    
    # Relacionamento para acessar o MenuItem diretamente nos templates (item.menu_item)
    menu_item = db.relationship('MenuItem', backref='order_items')
    
    def __repr__(self):
        return f'<OrderItem {self.id}>'

# Modelo para favoritos de restaurantes
class RestaurantFavorite(db.Model):
    __bind_key__ = 'restaurants'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column('usuario_id', db.Integer, nullable=False)
    restaurant_id = db.Column('restaurante_id', db.Integer, db.ForeignKey('restaurant.id'), nullable=False)
    created_at = db.Column('criado_em', db.DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    restaurant = db.relationship('Restaurant', backref=db.backref('favorited_by', lazy=True))
    
    # Constraint para evitar duplicatas
    __table_args__ = (db.UniqueConstraint('usuario_id', 'restaurante_id', name='unique_user_restaurant_favorite'),)
    
    def __repr__(self):
        return f'<RestaurantFavorite {self.user_id} -> {self.restaurant_id}>'

# Modelo para favoritos de produtos (itens de menu)
class ProductFavorite(db.Model):
    __bind_key__ = 'restaurants'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column('usuario_id', db.Integer, nullable=False)
    menu_item_id = db.Column('item_menu_id', db.Integer, db.ForeignKey('menu_item.id'), nullable=False)
    created_at = db.Column('criado_em', db.DateTime, default=datetime.utcnow)

    menu_item = db.relationship('MenuItem', backref=db.backref('favorited_by', lazy=True))

    __table_args__ = (db.UniqueConstraint('usuario_id', 'item_menu_id', name='unique_user_item_favorite'),)

    def __repr__(self):
        return f'<ProductFavorite {self.user_id} -> {self.menu_item_id}>'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Rotas
@app.route('/')
def index():
    q = request.args.get('q', '').strip()
    category = request.args.get('category', '').strip()
    query = Restaurant.query
    if q:
        query = query.filter(
            (Restaurant.name.ilike(f"%{q}%")) |
            (Restaurant.category.ilike(f"%{q}%")) |
            (Restaurant.address.ilike(f"%{q}%"))
        )
    if category:
        query = query.filter(Restaurant.category == category)
    restaurants = query.all()
    return render_template('index.html', restaurants=restaurants, q=q, selected_category=category)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        address = (request.form.get('address') or '').strip()
        mode = (request.form.get('mode', 'email') or 'email').strip()
        email = (request.form.get('email') or '').strip().lower() if mode == 'email' else None
        raw_phone = (request.form.get('phone') or '').strip()
        phone = None
        phone_digits = ''.join(ch for ch in raw_phone if ch.isdigit()) if raw_phone else ''
        if raw_phone.startswith('+'):
            phone = raw_phone
        elif phone_digits:
            if len(phone_digits) >= 10:
                phone = f"+55{phone_digits}"
            else:
                phone = phone_digits

        if not name:
            flash('Informe seu nome completo.')
            return redirect(url_for('register'))
        if not address:
            flash('Informe seu endereço completo.')
            return redirect(url_for('register'))

        # Validações por modo
        if mode == 'email':
            if not email:
                flash('Informe um email válido.')
                return redirect(url_for('register'))
            existing = User.query.filter_by(email=email).first()
            if existing:
                flash('Email já cadastrado.')
                return redirect(url_for('register'))
            contact_value = email
            send_method = 'email'
        else:
            if not phone:
                flash('Informe um telefone válido.')
                return redirect(url_for('register'))
            existing = User.query.filter_by(phone=phone).first()
            if existing:
                flash('Telefone já cadastrado.')
                return redirect(url_for('register'))
            contact_value = phone
            send_method = 'sms'

        new_user = User(name=name, email=email, password=None, address=address, phone=phone, is_verified=False)
        db.session.add(new_user)
        db.session.commit()

        if app.config.get('ALLOW_OPEN_ACCESS'):
            new_user.is_verified = True
            new_user.verification_code = None
            new_user.verification_code_expires = None
            db.session.commit()
            try:
                logout_user()
            except Exception:
                pass
            flash('Cadastro finalizado', 'success')
            return redirect(url_for('login'))
        else:
            verification_code = generate_verification_code()
            new_user.verification_code = verification_code
            new_user.verification_code_expires = datetime.utcnow() + timedelta(minutes=10)
            db.session.commit()
            session['last_verification_code'] = verification_code
            ok = send_verification_code(contact_value, verification_code, method=send_method)
            if not ok:
                app.config['SHOW_DEV_CODE'] = True
                flash('Não foi possível enviar o código. Exibimos o código na tela para você entrar.', 'warning')
            else:
                flash(f'Cadastro iniciado! Enviamos um código para seu {"email" if mode == "email" else "telefone"}.')
            return redirect(url_for('verify_code', user_id=new_user.id))

    return render_template('register.html')

# Função para gerar código de verificação de 6 dígitos
def generate_verification_code():
    return ''.join(random.choices(string.digits, k=6))

# Função para simular envio de código (em produção, usar serviços reais de email/SMS)
def send_email_code(to_email, code):
    # Primeiro tenta via Flask-Mail se configurado
    try:
        if app.config.get('MAIL_SERVER') and app.config.get('MAIL_USERNAME') and app.config.get('MAIL_PASSWORD'):
            msg = Message(subject='Seu código de verificação', recipients=[to_email], body=f'Seu código é: {code}')
            if app.config.get('MAIL_DEFAULT_SENDER'):
                msg.sender = app.config['MAIL_DEFAULT_SENDER']
            mail.send(msg)
            print(f"[EMAIL] Código enviado via Flask-Mail para {to_email} (server={app.config.get('MAIL_SERVER')}, port={app.config.get('MAIL_PORT')})")
            return True
    except Exception as e:
        print(f"[EMAIL][FLASK-MAIL] Erro ao enviar: {e}. Tentando fallback SMTP...")

    # Fallback: envio direto via SMTP usando variáveis SMTP_*
    host = os.environ.get('SMTP_HOST') or app.config.get('MAIL_SERVER')
    port = int(os.environ.get('SMTP_PORT') or str(app.config.get('MAIL_PORT') or '587'))
    user = os.environ.get('SMTP_USER') or app.config.get('MAIL_USERNAME')
    password = os.environ.get('SMTP_PASS') or os.environ.get('SMTP_PASSWORD') or app.config.get('MAIL_PASSWORD')
    if password:
        try:
            p = str(password)
            p = p.replace('-', '')
            p = ''.join(p.split())
            password = p
        except Exception:
            pass
    from_email = os.environ.get('SMTP_FROM') or os.environ.get('MAIL_FROM') or app.config.get('MAIL_DEFAULT_SENDER') or user
    secure = (os.environ.get('SMTP_SECURE') or ('ssl' if app.config.get('MAIL_USE_SSL') else 'tls')).lower()
    if not host or not user or not password:
        print('[ENV] SMTP/Flask-Mail não configurado; usando simulação no console.')
        print(f"[SIMULAÇÃO] Código {code} para {to_email} via email")
        return False

    def get_eta_time(self):
        try:
            mins = (self.restaurant.delivery_time or 0)
            return datetime.fromtimestamp(self.created_at.timestamp() + mins * 60)
        except Exception:
            return self.created_at
    msg_em = EmailMessage()
    msg_em['Subject'] = 'Seu código de verificação'
    msg_em['From'] = from_email
    msg_em['To'] = to_email
    msg_em.set_content(f'Seu código é: {code}')
    try:
        context = ssl.create_default_context()
        if secure == 'ssl' or port == 465:
            with smtplib.SMTP_SSL(host, port, context=context, timeout=10) as server:
                server.login(user, password)
                server.send_message(msg_em)
        else:
            with smtplib.SMTP(host, port, timeout=10) as server:
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
                server.login(user, password)
                server.send_message(msg_em)
        print(f"[EMAIL] Código enviado via SMTP para {to_email} (host={host}, port={port}, from={from_email})")
        return True
    except smtplib.SMTPAuthenticationError as e:
        print(f"[EMAIL][AUTH] Falha de autenticação SMTP: {e}")
        return False
    except smtplib.SMTPException as e:
        print(f"[EMAIL][SMTP] Erro SMTP: {e}")
        return False
    except Exception as e:
        print(f"[EMAIL][ERRO] {e}")
        return False

def send_email_mailtrap(to_email, code):
    host = os.environ.get('MAIL_SERVER') or 'live.smtp.mailtrap.io'
    port = int(os.environ.get('MAIL_PORT') or '587')
    user = os.environ.get('MAIL_USERNAME') or 'api'
    password = os.environ.get('MAIL_PASSWORD') or os.environ.get('MAILER_API_TOKEN') or ''
    if not password:
        return False
    msg = MIMEText(f"Seu código de verificação é: {code}")
    msg['Subject'] = 'Código de verificação'
    msg['From'] = os.environ.get('MAIL_DEFAULT_SENDER') or 'no-reply@localhost.test'
    msg['To'] = to_email
    try:
        with smtplib.SMTP(host, port, timeout=10) as server:
            server.ehlo()
            server.starttls(context=ssl.create_default_context())
            server.ehlo()
            server.login(user, password)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"[MAILTRAP][ERRO] {e}")
        return False

def send_sms_code(to_phone, code):
    sid = os.environ.get('TWILIO_ACCOUNT_SID')
    token = os.environ.get('TWILIO_AUTH_TOKEN')
    from_number = os.environ.get('TWILIO_FROM_NUMBER')
    whatsapp_from = os.environ.get('TWILIO_WHATSAPP_FROM')
    channel = os.environ.get('TWILIO_CHANNEL', 'sms')
    if not sid or not token or (not from_number and not whatsapp_from):
        print('[ENV] Twilio não configurado; usando simulação no console.')
        print(f"[SIMULAÇÃO] Código {code} para {to_phone} via {channel}")
        return False
    try:
        url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
        to_value = to_phone
        from_value = from_number
        if channel == 'whatsapp' and whatsapp_from:
            from_value = whatsapp_from
            if not to_phone.startswith('whatsapp:'):
                to_value = f"whatsapp:{to_phone}"
        data = {
            'Body': f'Seu código de verificação é: {code}',
            'To': to_value,
            'From': from_value,
        }
        resp = requests.post(url, data=data, auth=(sid, token), timeout=10)
        if 200 <= resp.status_code < 300:
            sid_resp = resp.json().get('sid')
            print(f"[SMS] Mensagem SID: {sid_resp}")
            return True
        else:
            print(f"[SMS][ERRO] Status {resp.status_code}: {resp.text}")
            return False
    except Exception as e:
        print(f"[SMS][ERRO] {e}")
        return False

def send_verification_code(recipient, code, method='email'):
    """Envia o código por email ou telefone (SMS/WhatsApp), conforme método."""
    if method == 'email':
        return send_email_code(recipient, code)
    elif method in ('sms', 'phone', 'whatsapp'):
        return send_sms_code(recipient, code)
    else:
        print(f"[AVISO] Método '{method}' desconhecido. Simulando envio.")
        print(f"[SIMULAÇÃO] Código {code} para {recipient} via {method}")
        return False

# Rota de teste rápido para envio de email
@app.route('/debug/send-email', methods=['POST', 'GET'])
def debug_send_email():
    to = request.values.get('to')
    code = request.values.get('code') or generate_verification_code()
    if not to:
        return jsonify({'ok': False, 'error': 'Informe o destinatário com ?to=seuemail@dominio.com ou via form-data'}), 400
    ok = send_email_code(to, code)
    return jsonify({'ok': ok, 'to': to, 'code': code})

@app.route('/enviar_codigo', methods=['POST'])
def enviar_codigo():
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    role = (data.get('role') or 'customer').strip().lower()
    is_restaurant = True if role == 'restaurant' else False
    if not email:
        return jsonify({'status': 'Informe email'}), 400
    user = User.query.filter_by(email=email, is_restaurant=is_restaurant).first()
    if not user:
        new_user = User(name=(email.split('@')[0] or 'Usuário'), email=email, is_restaurant=is_restaurant, is_verified=False)
        db.session.add(new_user)
        db.session.commit()
        user = new_user
    code = generate_verification_code()
    user.verification_code = code
    user.verification_code_expires = datetime.utcnow() + timedelta(minutes=10)
    db.session.commit()
    session['last_verification_code'] = code
    ok = send_verification_code(email, code, method='email')
    verify_url = url_for('verify_code', user_id=user.id)
    return jsonify({'status': 'Código enviado' if ok else 'Falha ao enviar', 'ok': ok, 'code': (code if app.config.get('SHOW_DEV_CODE') else None), 'verify_url': verify_url, 'user_id': user.id})

@app.route('/verificar_codigo', methods=['POST'])
def verificar_codigo_api():
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    user_id_raw = data.get('user_id')
    code = (data.get('code') or '').strip()
    if not code or (not email and not user_id_raw):
        return jsonify({'status': 'Dados insuficientes'}), 400
    user = None
    if user_id_raw:
        try:
            user = User.query.get(int(user_id_raw))
        except Exception:
            user = None
    if not user and email:
        user = User.query.filter_by(email=email).first()
    if not user or not user.verification_code or not user.verification_code_expires:
        return jsonify({'status': 'Código inválido ou usuário não encontrado'}), 400
    ok = (user.verification_code == code and datetime.utcnow() < user.verification_code_expires)
    if ok:
        user.verification_code = None
        user.verification_code_expires = None
        user.is_verified = True
        db.session.commit()
        return jsonify({'status': 'Verificado!', 'user_id': user.id})
    return jsonify({'status': 'Código incorreto!'}), 400

@app.route('/debug/routes')
def debug_routes():
    rules = []
    for r in app.url_map.iter_rules():
        rules.append({'rule': str(r), 'methods': sorted(list(r.methods))})
    return jsonify({'count': len(rules), 'routes': rules})

@app.route('/debug/mail-info')
def debug_mail_info():
    try:
        info = {
            'server': app.config.get('MAIL_SERVER'),
            'port': app.config.get('MAIL_PORT'),
            'use_tls': app.config.get('MAIL_USE_TLS'),
            'use_ssl': app.config.get('MAIL_USE_SSL'),
            'username_set': bool(app.config.get('MAIL_USERNAME')),
            'default_sender': app.config.get('MAIL_DEFAULT_SENDER'),
        }
        return jsonify({'ok': True, 'mail': info})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})

@app.route('/debug/set-mail', methods=['POST'])
def debug_set_mail():
    try:
        data = request.get_json(silent=True) or request.form or {}
        def pick(*keys, default=None):
            for k in keys:
                v = data.get(k)
                if v is not None and v != '':
                    return v
            return default
        def to_bool(v, default=False):
            if v is None:
                return default
            s = str(v).strip().lower()
            return s in ('1','true','yes','y','on')
        server = pick('server','MAIL_SERVER','SMTP_HOST', default=app.config.get('MAIL_SERVER'))
        port = pick('port','MAIL_PORT','SMTP_PORT', default=app.config.get('MAIL_PORT') or 587)
        try:
            port = int(str(port))
        except Exception:
            port = 587
        username = pick('username','MAIL_USERNAME','SMTP_USER', default=app.config.get('MAIL_USERNAME'))
        password = pick('password','MAIL_PASSWORD','SMTP_PASS','SMTP_PASSWORD', default=app.config.get('MAIL_PASSWORD'))
        default_sender = pick('default_sender','MAIL_DEFAULT_SENDER','SMTP_FROM','MAIL_FROM', default=username)
        secure = (pick('secure','SMTP_SECURE', default='').strip().lower())
        use_ssl = to_bool(pick('use_ssl','MAIL_USE_SSL', default=None)) if pick('use_ssl','MAIL_USE_SSL', default=None) is not None else (secure == 'ssl' or port == 465)
        use_tls = to_bool(pick('use_tls','MAIL_USE_TLS', default=None)) if pick('use_tls','MAIL_USE_TLS', default=None) is not None else (not use_ssl)
        app.config['MAIL_SERVER'] = server or 'smtp.gmail.com'
        app.config['MAIL_PORT'] = port
        app.config['MAIL_USE_SSL'] = bool(use_ssl)
        app.config['MAIL_USE_TLS'] = bool(use_tls)
        app.config['MAIL_USERNAME'] = username
        app.config['MAIL_PASSWORD'] = password
        app.config['MAIL_DEFAULT_SENDER'] = default_sender or username
        try:
            mail.init_app(app)
        except Exception:
            pass
        info = {
            'server': app.config.get('MAIL_SERVER'),
            'port': app.config.get('MAIL_PORT'),
            'use_tls': app.config.get('MAIL_USE_TLS'),
            'use_ssl': app.config.get('MAIL_USE_SSL'),
            'username_set': bool(app.config.get('MAIL_USERNAME')),
            'default_sender': app.config.get('MAIL_DEFAULT_SENDER'),
        }
        return jsonify({'ok': True, 'mail': info})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})

@app.route('/debug/set-google-oauth', methods=['POST'])
def debug_set_google_oauth():
    try:
        if not OAUTH_AVAILABLE:
            return jsonify({'ok': False, 'error': 'OAuth indisponível'}), 400
        data = request.get_json(silent=True) or request.form or {}
        cid = (data.get('client_id') or data.get('GOOGLE_OAUTH_CLIENT_ID') or '').strip()
        csec = (data.get('client_secret') or data.get('GOOGLE_OAUTH_CLIENT_SECRET') or '').strip()
        if not cid or not csec:
            return jsonify({'ok': False, 'error': 'Informe client_id e client_secret'}), 400
        app.config['GOOGLE_OAUTH_CLIENT_ID'] = cid
        app.config['GOOGLE_OAUTH_CLIENT_SECRET'] = csec
        try:
            google_bp.client_id = cid
            google_bp.client_secret = csec
        except Exception:
            pass
        try:
            google_bp.authorization_url_params = {"prompt": "select_account"}
        except Exception:
            pass
        try:
            google_bp.storage = SQLAlchemyStorage(OAuth, db.session, user=current_user, user_required=False)
        except Exception:
            pass
        redirect_uri = None
        try:
            redirect_uri = url_for('google.authorized', _external=True)
        except Exception:
            redirect_uri = '/login/google/authorized'
        return jsonify({'ok': True, 'redirect_uri': redirect_uri, 'client_id_set': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400

@app.route('/debug/oauth-info')
def debug_oauth_info():
    try:
        info = {
            'oauth_available': OAUTH_AVAILABLE,
        }
        if OAUTH_AVAILABLE:
            cid = app.config.get('GOOGLE_OAUTH_CLIENT_ID')
            csec = app.config.get('GOOGLE_OAUTH_CLIENT_SECRET')
            info['google_client_id_set'] = bool(cid and cid not in ('seu-client-id-aqui', ''))
            info['google_client_secret_set'] = bool(csec and csec not in ('seu-client-secret-aqui', ''))
            try:
                info['google_redirect_uri'] = url_for('google.authorized', _external=True)
            except Exception:
                info['google_redirect_uri'] = '/login/google/authorized'
        return jsonify({'ok': True, 'info': info})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})

@app.route('/debug/oauth-reset', methods=['POST'])
def debug_oauth_reset():
    try:
        session.pop('google_oauth_state', None)
        session.pop('google_oauth_token', None)
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})

@app.errorhandler(MismatchingStateError)
def handle_oauth_state_mismatch(e):
    try:
        session.pop('google_oauth_state', None)
        session.pop('google_oauth_token', None)
    except Exception:
        pass
    flash('Sessão OAuth inválida ou expirada. Por favor, tente novamente.', 'warning')
    return redirect(url_for('google_login'))

@app.route('/debug/show-code/<int:user_id>')
def debug_show_code(user_id):
    user = User.query.get_or_404(user_id)
    return jsonify({
        'ok': True,
        'user_id': user.id,
        'has_email': bool(user.email),
        'has_phone': bool(user.phone),
        'code': user.verification_code,
        'expires_at': user.verification_code_expires.isoformat() if user.verification_code_expires else None
    })

@app.route('/debug/send-sms', methods=['POST', 'GET'])
def debug_send_sms():
    to = request.values.get('to')
    channel = (request.values.get('channel') or os.environ.get('TWILIO_CHANNEL') or 'sms').strip()
    code = request.values.get('code') or generate_verification_code()
    if not to:
        return jsonify({'ok': False, 'error': 'Informe o destinatário com ?to=+55XXXXXXXXXX ou via form-data', 'channel': channel}), 400
    ok = send_sms_code(to, code)
    return jsonify({'ok': ok, 'to': to, 'code': code, 'channel': channel})

@app.route('/login', methods=['GET', 'POST'])
def login():
    def is_safe_next(url: str) -> bool:
        try:
            return url and url.startswith('/') and '//' not in url
        except Exception:
            return False
    next_url = request.args.get('next') or request.form.get('next')
    if request.method == 'POST':
        role = (request.form.get('role') or 'customer').strip()  # 'customer' ou 'restaurant'
        mode = (request.form.get('mode') or 'email').strip()      # 'email' ou 'phone'
        email = request.form.get('email', '').strip()
        raw_phone = request.form.get('phone', '').strip()
        phone_digits = ''.join(ch for ch in raw_phone if ch.isdigit()) if raw_phone else ''
        if raw_phone.startswith('+'):
            phone = raw_phone
        elif phone_digits:
            phone = f"+55{phone_digits}" if len(phone_digits) >= 10 else phone_digits
        else:
            phone = ''
        
        is_restaurant = True if role == 'restaurant' else False
        user = None
        contact_value = None
        send_method = 'email'

        if mode == 'email' and email:
            contact_value = email
            user = User.query.filter_by(email=email, is_restaurant=is_restaurant).first()
            send_method = 'email'
        elif mode == 'phone' and phone:
            contact_value = phone
            user = User.query.filter_by(phone=phone, is_restaurant=is_restaurant).first()
            send_method = 'sms'
        else:
            flash('Informe email ou telefone corretamente para entrar.')
            return redirect(url_for('login'))

        if not user:
            name_value = (email.split('@')[0] if (mode == 'email' and email) else phone)
            new_user = User(name=name_value or 'Usuário', email=(email if mode == 'email' else None), phone=(phone if mode == 'phone' else None), is_restaurant=is_restaurant, is_verified=False)
            db.session.add(new_user)
            db.session.commit()
            user = new_user

        if app.config.get('ALLOW_OPEN_ACCESS'):
            user.is_verified = True
            user.verification_code = None
            user.verification_code_expires = None
            db.session.commit()
            login_user(user)
            flash('Cadastro finalizado', 'success')
            if is_safe_next(next_url):
                return redirect(next_url)
            return redirect(url_for('index'))
        else:
            flash('Conta sem senha: enviaremos um código para confirmar.', 'info')
            verification_code = generate_verification_code()
            user.verification_code = verification_code
            user.verification_code_expires = datetime.utcnow() + timedelta(minutes=10)
            db.session.commit()
            session['last_verification_code'] = verification_code
            ok = send_verification_code(contact_value, verification_code, method=send_method)
            destino = 'email' if mode == 'email' else 'telefone'
            if not ok:
                app.config['SHOW_DEV_CODE'] = True
                flash(f'Não foi possível enviar para seu {destino}. Exibimos o código na tela para você entrar.', 'warning')
            else:
                flash(f'Código de verificação enviado para seu {destino}. Confira e digite o código para entrar.')
            if is_safe_next(next_url):
                session['post_login_next'] = next_url
            return redirect(url_for('verify_code', user_id=user.id))
    
    return render_template('login.html', oauth_available=OAUTH_AVAILABLE)

@app.route('/verify-code/<int:user_id>', methods=['GET', 'POST'])
def verify_code(user_id):
    user = User.query.get_or_404(user_id)
    next_route = request.args.get('next', '').strip()
    
    if request.method == 'POST':
        entered_code = request.form.get('verification_code')
        
        # Verificar se o código está correto e não expirou
        if (user.verification_code == entered_code and 
            user.verification_code_expires and 
            datetime.utcnow() < user.verification_code_expires):
            
            # Limpar código de verificação e marcar como verificado
            user.verification_code = None
            user.verification_code_expires = None
            user.is_verified = True
            db.session.commit()
            
            login_user(user)
            flash('Login realizado com sucesso!')
            next_url = session.pop('post_login_next', None)
            if next_url and next_url.startswith('/') and '//' not in next_url:
                return redirect(next_url)
            if next_route:
                try:
                    return redirect(url_for(next_route))
                except Exception:
                    return redirect(url_for('index'))
            return redirect(url_for('index'))
        else:
            flash('Código inválido ou expirado. Tente novamente.')
    
    dev_code = user.verification_code or session.get('last_verification_code')
    return render_template(
        'verify_code.html',
        user=user,
        show_dev_code=True,
        dev_code=dev_code,
        has_phone=bool(user.phone),
        has_email=bool(user.email)
    )

@app.route('/resend-code/<int:user_id>', methods=['POST'])
def resend_code(user_id):
    user = User.query.get_or_404(user_id)
    method = (request.form.get('method') or request.args.get('method') or ('email' if user.email else 'sms')).strip()
    recipient = user.email if method == 'email' else user.phone

    # Gerar novo código
    verification_code = generate_verification_code()
    user.verification_code = verification_code
    user.verification_code_expires = datetime.utcnow() + timedelta(minutes=10)
    db.session.commit()
    session['last_verification_code'] = verification_code

    # Enviar conforme método escolhido (ou simular em dev)
    ok = send_verification_code(recipient, verification_code, method=method)

    canal_texto = 'email' if method == 'email' else ('WhatsApp' if method == 'whatsapp' else 'SMS')
    if ok:
        flash(f'Novo código enviado por {canal_texto}!', 'success')
    else:
        app.config['SHOW_DEV_CODE'] = True
        flash(f'Não foi possível enviar por {canal_texto}. Exibimos o código na tela para você entrar.', 'warning')
    return redirect(url_for('verify_code', user_id=user.id))

@app.route('/logout')
@login_required
def logout():
    try:
        if OAUTH_AVAILABLE:
            try:
                google_bp.storage.set(None)
            except Exception:
                pass
        session.pop('google_oauth_token', None)
        session.pop('google_oauth_state', None)
    except Exception:
        pass
    logout_user()
    return redirect(url_for('index'))

@app.route('/register/restaurant', methods=['GET', 'POST'])
def register_restaurant():
    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        email = (request.form.get('email') or '').strip().lower()
        phone = (request.form.get('phone') or '').strip()

        if not name or not email:
            flash('Informe nome e email para cadastrar a conta de restaurante.', 'warning')
            return redirect(url_for('register_restaurant'))

        user_exists = User.query.filter_by(email=email).first()
        if user_exists:
            flash('Email já cadastrado.')
            return redirect(url_for('register_restaurant'))

        new_user = User(name=name, email=email, password=None, phone=phone, is_restaurant=True, is_verified=True)
        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)
        flash('Conta de restaurante criada! Agora cadastre seu restaurante.', 'success')
        return redirect(url_for('create_restaurant'))

    return render_template('restaurant_register.html', oauth_available=OAUTH_AVAILABLE)

@app.route('/login/google/start')
def google_login():
    if not OAUTH_AVAILABLE:
        flash('Login social não está disponível nesta instalação.', 'warning')
        return redirect(url_for('login'))
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

    role = (request.args.get('role') or '').strip().lower()
    desired_is_restaurant = True if role == 'restaurant' else False
    # Verificar se o usuário está autorizado
    if request.args.get('force') == '1':
        try:
            google_bp.storage.set(None)
        except Exception:
            session.pop('google_oauth_token', None)
        try:
            session.pop('google_oauth_state', None)
        except Exception:
            pass
        try:
            google_bp.authorization_url_params = {"prompt": "consent select_account", "access_type": "offline", "include_granted_scopes": "true"}
        except Exception:
            pass
        session['oauth_role_is_restaurant'] = desired_is_restaurant
        return redirect(url_for('google.login'))
    if not google.authorized:
        # Guardar intenção de perfil antes de iniciar OAuth
        session['oauth_role_is_restaurant'] = desired_is_restaurant
        return redirect(url_for('google.login'))
    
    try:
        resp = google.get('/oauth2/v2/userinfo')
        if not resp.ok:
            if getattr(resp, 'status_code', None) == 401:
                return redirect(url_for('google.login'))
            flash(f'Erro ao obter dados do Google. Status: {getattr(resp, "status_code", "?")}', 'danger')
            return redirect(url_for('login'))
            
        user_info = resp.json()
        
        # Verificar se temos as informações necessárias
        if 'email' not in user_info:
            flash('Não foi possível obter o email da conta Google.', 'danger')
            return redirect(url_for('login'))
            
        email = user_info['email']
        name = user_info.get('name', email.split('@')[0])  # Fallback para nome
        
        # Verificar se o usuário já existe
        user = User.query.filter_by(email=email).first()
        
        if not user:
            user = User(
                name=name,
                email=email,
                social_id=user_info.get('id'),
                social_provider='google',
                password=None,
                is_restaurant=session.get('oauth_role_is_restaurant', desired_is_restaurant),
                is_verified=False
            )
            db.session.add(user)
            db.session.commit()
            flash('Conta criada com sucesso usando Google. Enviamos um código para confirmar.', 'success')
        else:
            # Atualizar informações sociais se necessário
            if not user.social_id:
                user.social_id = user_info.get('id')
                user.social_provider = 'google'
                db.session.commit()
        
        # Gerar e enviar código de verificação para o email do Google
        verification_code = generate_verification_code()
        user.verification_code = verification_code
        user.verification_code_expires = datetime.utcnow() + timedelta(minutes=10)
        db.session.commit()
        session['last_verification_code'] = verification_code
        ok = send_verification_code(email, verification_code, method='email')
        if not ok:
            app.config['SHOW_DEV_CODE'] = True
            flash('Não foi possível enviar o email com o código. Exibimos o código na tela para você entrar.', 'warning')
        else:
            flash('Código de verificação enviado para seu email Google. Confira e digite o código para entrar.')
        
        # Redirecionar para verificação de código
        next_url = request.args.get('next')
        if next_url and next_url.startswith('/') and '//' not in next_url:
            session['post_login_next'] = next_url
        return redirect(url_for('verify_code', user_id=user.id))
        
    except Exception as e:
        # Log do erro para debug
        print(f"Erro no login Google: {str(e)}")
        flash('Ocorreu um erro durante o login com Google. Tente novamente.', 'danger')
        return redirect(url_for('login'))

@app.route('/login/google/choose')
def google_choose_account():
    if not OAUTH_AVAILABLE:
        return redirect(url_for('login'))
    role = (request.args.get('role') or '').strip().lower()
    desired_is_restaurant = True if role == 'restaurant' else False
    session['oauth_role_is_restaurant'] = desired_is_restaurant
    try:
        google_bp.storage.set(None)
    except Exception:
        session.pop('google_oauth_token', None)
    try:
        session.pop('google_oauth_state', None)
    except Exception:
        pass
    try:
        google_bp.authorization_url_params = {"prompt": "consent select_account", "access_type": "offline", "include_granted_scopes": "true"}
    except Exception:
        pass
    return redirect(url_for('google.login'))

@app.route('/login/facebook/start')
def facebook_login():
    if not OAUTH_AVAILABLE:
        flash('Login social não está disponível nesta instalação.', 'warning')
        return redirect(url_for('login'))
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
        user = User.query.filter_by(email=email).first()
        if not user:
            user = User(
                name=user_info.get('name') or (email.split('@')[0]),
                email=email,
                social_id=user_info.get('id'),
                social_provider='facebook',
                password=None,
                is_restaurant=True,
                is_verified=False
            )
            db.session.add(user)
            db.session.commit()
            flash('Conta criada com sucesso usando Facebook. Enviamos um código para confirmar.', 'success')
        else:
            if not user.social_id:
                user.social_id = user_info.get('id')
                user.social_provider = 'facebook'
                db.session.commit()
        verification_code = generate_verification_code()
        user.verification_code = verification_code
        user.verification_code_expires = datetime.utcnow() + timedelta(minutes=10)
        db.session.commit()
        session['last_verification_code'] = verification_code
        ok = send_verification_code(email, verification_code, method='email')
        if not ok:
            app.config['SHOW_DEV_CODE'] = True
            flash('Não foi possível enviar o email com o código. Exibimos o código na tela para você entrar.', 'warning')
        else:
            flash('Código de verificação enviado para seu email Facebook. Confira e digite o código para entrar.')
        next_url = request.args.get('next')
        if next_url and next_url.startswith('/') and '//' not in next_url:
            session['post_login_next'] = next_url
        return redirect(url_for('verify_code', user_id=user.id))
    
    try:
        error_text = resp.text if hasattr(resp, 'text') else str(resp)
        flash(f'Falha ao fazer login com Facebook. Código: {getattr(resp, "status_code", "?")}. Detalhes: {error_text}', 'danger')
    except Exception:
        flash('Falha ao fazer login com Facebook.', 'danger')
    return redirect(url_for('login'))

@app.route('/restaurant/<int:restaurant_id>')
def restaurant(restaurant_id):
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    
    # Parâmetros de filtro
    category = request.args.get('category', '').strip()
    min_price_raw = request.args.get('min_price', '').strip()
    max_price_raw = request.args.get('max_price', '').strip()
    available_only = request.args.get('available', '').strip() == 'true'
    sort_by = request.args.get('sort', 'name')  # name, price_asc, price_desc, category
    
    # Query base
    query = MenuItem.query.filter_by(restaurant_id=restaurant_id)
    
    # Aplicar filtros
    if category:
        query = query.filter(MenuItem.category == category)
    
    min_price = parse_float(min_price_raw)
    max_price = parse_float(max_price_raw)
    if min_price is not None:
        query = query.filter(MenuItem.price >= min_price)
    if max_price is not None:
        query = query.filter(MenuItem.price <= max_price)
    
    if available_only:
        query = query.filter(MenuItem.available == True)
    
    # Aplicar ordenação
    if sort_by == 'price_asc':
        query = query.order_by(MenuItem.price.asc())
    elif sort_by == 'price_desc':
        query = query.order_by(MenuItem.price.desc())
    elif sort_by == 'category':
        query = query.order_by(MenuItem.category.asc(), MenuItem.name.asc())
    else:  # name
        query = query.order_by(MenuItem.name.asc())
    
    menu_items = query.all()
    
    # Obter todas as categorias disponíveis para o filtro
    all_categories = db.session.query(MenuItem.category).filter_by(restaurant_id=restaurant_id).distinct().all()
    categories = [cat[0] for cat in all_categories if cat[0]]
    
    return render_template('restaurant.html', 
                         restaurant=restaurant, 
                         menu_items=menu_items,
                         categories=categories,
                         selected_category=category,
                         min_price=min_price_raw,
                         max_price=max_price_raw,
                         available_only=available_only,
                         sort_by=sort_by)

@app.route('/cart')
@login_required
def cart():
    cart = Cart.query.filter_by(user_id=current_user.id).order_by(Cart.updated_at.desc()).first()
    available_items = []
    if cart:
        try:
            available_items = (
                MenuItem.query
                .filter_by(restaurant_id=cart.restaurant_id, available=True)
                .order_by(MenuItem.name.asc())
                .limit(8)
                .all()
            )
        except Exception:
            available_items = []
    return render_template('cart.html', cart=cart, available_items=available_items)

@app.route('/add_to_cart', methods=['POST', 'GET'])
@login_required
def add_to_cart():
    if request.method == 'GET':
        item_id_raw = request.args.get('item_id')
        quantity_raw = request.args.get('quantity')
        is_form = True
        data = None
    else:
        data = request.get_json(silent=True)
        is_form = not bool(data)
        item_id_raw = (data or {}).get('item_id') or request.form.get('item_id')
        quantity_raw = (data or {}).get('quantity') or request.form.get('quantity')
    try:
        item_id = int(item_id_raw)
    except Exception:
        abort(400)
    try:
        quantity = int(quantity_raw) if quantity_raw is not None else 1
    except Exception:
        quantity = 1
    
    menu_item = MenuItem.query.get_or_404(item_id)
    
    # Buscar ou criar carrinho para este restaurante
    cart = Cart.query.filter_by(
        user_id=current_user.id,
        restaurant_id=menu_item.restaurant_id
    ).first()
    
    if not cart:
        # Verificar se há carrinho de outro restaurante e limpar somente se for de outro restaurante
        existing_cart = Cart.query.filter_by(user_id=current_user.id).order_by(Cart.updated_at.desc()).first()
        if existing_cart and existing_cart.restaurant_id != menu_item.restaurant_id:
            db.session.delete(existing_cart)
            db.session.commit()
        
        cart = Cart(
            user_id=current_user.id,
            restaurant_id=menu_item.restaurant_id
        )
        db.session.add(cart)
        db.session.commit()
    
    # Verificar se item já existe no carrinho
    cart_item = CartItem.query.filter_by(cart_id=cart.id, menu_item_id=item_id).first()
    
    if cart_item:
        cart_item.quantity += quantity
    else:
        cart_item = CartItem(
            cart_id=cart.id,
            menu_item_id=item_id,
            quantity=quantity,
            price=menu_item.price
        )
        db.session.add(cart_item)
    
    cart.updated_at = datetime.utcnow()
    db.session.commit()
    
    if is_form:
        return redirect(url_for('cart'))
    return jsonify({'success': True, 'cart_count': cart.get_item_count(), 'cart_total': cart.get_total()})

@app.route('/update_cart_item', methods=['POST'])
@login_required
def update_cart_item():
    data = request.get_json(silent=True)
    is_form = not bool(data)
    if not data:
        item_ref = request.form.get('item_id')
        quantity = parse_int(request.form.get('quantity')) or 1
        cart_item = CartItem.query.get(item_ref)
        if cart_item is None or cart_item.cart.user_id != current_user.id:
            return redirect(url_for('cart'))
        cart = Cart.query.get(cart_item.cart_id)
        if cart is None:
            return redirect(url_for('cart'))
    else:
        item_ref = data.get('item_id')
        quantity = int(data.get('quantity', 1))
        cart = Cart.query.filter_by(user_id=current_user.id).first()
        if not cart:
            return jsonify({'success': False, 'message': 'Carrinho não encontrado'})
        cart_item = CartItem.query.filter_by(cart_id=cart.id, menu_item_id=item_ref).first()
    if not cart_item:
        return jsonify({'success': False, 'message': 'Item não encontrado no carrinho'})
    if quantity <= 0:
        db.session.delete(cart_item)
    else:
        cart_item.quantity = quantity
    cart.updated_at = datetime.utcnow()
    db.session.commit()
    if is_form:
        return redirect(url_for('cart'))
    return jsonify({'success': True, 'cart_count': cart.get_item_count(), 'cart_total': cart.get_total()})

@app.route('/remove_from_cart', methods=['POST'])
@login_required
def remove_from_cart():
    data = request.get_json(silent=True)
    is_form = not bool(data)
    cart = Cart.query.filter_by(user_id=current_user.id).first()
    if not cart:
        return redirect(url_for('cart')) if is_form else jsonify({'success': False, 'message': 'Carrinho não encontrado'})
    if data:
        item_ref = data.get('item_id')
        cart_item = CartItem.query.filter_by(cart_id=cart.id, menu_item_id=item_ref).first()
    else:
        item_ref = request.form.get('item_id')
        cart_item = CartItem.query.get(item_ref)
        if cart_item and cart_item.cart_id != cart.id:
            cart_item = None
    if cart_item:
        db.session.delete(cart_item)
        cart.updated_at = datetime.utcnow()
        db.session.commit()
    if is_form:
        return redirect(url_for('cart'))
    return jsonify({'success': True, 'cart_count': cart.get_item_count(), 'cart_total': cart.get_total()})

@app.route('/clear_cart', methods=['POST'])
@login_required
def clear_cart():
    cart = Cart.query.filter_by(user_id=current_user.id).first()
    if cart:
        db.session.delete(cart)
        db.session.commit()
    return jsonify({'success': True})

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    cart = Cart.query.filter_by(user_id=current_user.id).first()
    if not cart or not cart.items:
        flash('Seu carrinho está vazio!', 'warning')
        return redirect(url_for('index'))
    
    # Buscar endereços do usuário
    addresses = UserAddress.query.filter_by(user_id=current_user.id).all()
    default_address = UserAddress.query.filter_by(
        user_id=current_user.id,
        is_default=True
    ).first()
    
    if request.method == 'POST':
        address_id = request.form.get('address_id')
        payment_method = request.form.get('payment_method')
        notes = request.form.get('notes', '')
        card_name = (request.form.get('card_name') or '').strip()
        card_number = (request.form.get('card_number') or '').replace(' ', '')
        card_expiry = (request.form.get('card_expiry') or '').strip()
        card_cvv = (request.form.get('card_cvv') or '').strip()
        
        if not address_id:
            flash('Selecione um endereço de entrega!', 'danger')
            return render_template('checkout.html', cart=cart, addresses=addresses, default_address=default_address)
        
        if not payment_method:
            flash('Selecione uma forma de pagamento!', 'danger')
            return render_template('checkout.html', cart=cart, addresses=addresses, default_address=default_address)
        if payment_method in ('credit_card', 'debit_card'):
            if not card_name or not card_number or not card_expiry or not card_cvv:
                flash('Informe os dados do cartão.', 'danger')
                return render_template('checkout.html', cart=cart, addresses=addresses, default_address=default_address)
        
        # Calcular valores
        subtotal = cart.get_total()
        delivery_fee = cart.restaurant.delivery_fee
        total = subtotal + delivery_fee
        
        # Validar pagamento (sandbox)
        if not validate_payment(payment_method, total):
            flash('Falha na validação do pagamento. Verifique o método selecionado e tente novamente.', 'danger')
            return render_template('checkout.html', cart=cart, addresses=addresses, default_address=default_address)

        # Criar pedido
        order = Order(
            user_id=current_user.id,
            restaurant_id=cart.restaurant_id,
            address_id=address_id,
            subtotal=subtotal,
            delivery_fee=delivery_fee,
            total=total,
            payment_method=payment_method,
            notes=notes
        )
        db.session.add(order)
        db.session.flush()  # Para obter o ID do pedido
        
        # Criar itens do pedido
        for cart_item in cart.items:
            order_item = OrderItem(
                order_id=order.id,
                menu_item_id=cart_item.menu_item_id,
                quantity=cart_item.quantity,
                price=cart_item.price
            )
            db.session.add(order_item)
        
        # Limpar carrinho
        db.session.delete(cart)
        db.session.commit()
        
        flash('Pedido realizado com sucesso!', 'success')
        return redirect(url_for('order_invoice', order_id=order.id))
    
    return render_template('checkout.html', cart=cart, addresses=addresses, default_address=default_address)

@app.route('/orders')
@login_required
def orders():
    user_orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    address_by_order = {}
    for o in user_orders:
        try:
            address_by_order[o.id] = UserAddress.query.get(o.address_id)
        except Exception:
            address_by_order[o.id] = None
    cart = Cart.query.filter_by(user_id=current_user.id).order_by(Cart.updated_at.desc()).first()
    return render_template('orders.html', orders=user_orders, address_by_order=address_by_order, cart=cart)

@app.route('/orders/<int:order_id>/reorder', methods=['POST'])
@login_required
def reorder_order(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id and not current_user.is_admin:
        flash('Você não tem permissão para refazer este pedido.', 'danger')
        return redirect(url_for('orders'))
    existing_cart = Cart.query.filter_by(user_id=current_user.id).first()
    if existing_cart and existing_cart.restaurant_id != order.restaurant_id:
        db.session.delete(existing_cart)
        db.session.commit()
    cart = Cart.query.filter_by(user_id=current_user.id, restaurant_id=order.restaurant_id).first()
    if not cart:
        cart = Cart(user_id=current_user.id, restaurant_id=order.restaurant_id)
        db.session.add(cart)
        db.session.commit()
    CartItem.query.filter_by(cart_id=cart.id).delete()
    db.session.commit()
    for oi in order.items:
        db.session.add(CartItem(cart_id=cart.id, menu_item_id=oi.menu_item_id, quantity=oi.quantity, price=oi.price))
    cart.updated_at = datetime.utcnow()
    db.session.commit()
    flash('Itens adicionados ao carrinho a partir do pedido.', 'success')
    return redirect(url_for('cart'))

# Debug de pagamento
@app.route('/debug/payment')
def debug_payment():
    method = request.args.get('method', 'pix')
    try:
        total = float(request.args.get('total', '10.0'))
    except Exception:
        total = 0.0
    ok = validate_payment(method, total)
    return jsonify({'ok': ok, 'method': method, 'total': total})

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

# Gerar Nota Fiscal do pedido
@app.route('/orders/<int:order_id>/invoice')
@login_required
def order_invoice(order_id):
    order = Order.query.get_or_404(order_id)
    
    # Verificar permissões: dono do pedido, dono do restaurante ou admin
    if (order.user_id != current_user.id and 
        order.restaurant.owner_id != current_user.id and 
        not current_user.is_admin):
        flash('Você não tem permissão para visualizar esta nota fiscal.', 'danger')
        return redirect(url_for('orders'))
    
    # Permitir emissão para pedidos fechados (pendente, confirmado, entregue)
    # Em aulas/demo, liberamos a visualização da NF logo após o fechamento
    
    # Dados da empresa (simulados)
    company_data = {
        'name': 'Food Delivery App',
        'cnpj': '12.345.678/0001-90',
        'address': 'Rua das Entregas, 123 - Centro',
        'city': 'São Paulo - SP',
        'zip_code': '01234-567',
        'phone': '(11) 1234-5678',
        'email': 'contato@deliveryapp.com'
    }
    
    # Número da nota fiscal (baseado no ID do pedido)
    invoice_number = f"NF-{order.id:06d}"
    
    # Resolver dados de cliente e endereço em base de usuários
    order_user = User.query.get(order.user_id)
    order_address = UserAddress.query.get(order.address_id)
    return render_template('invoice.html', 
                         order=order,
                         order_user=order_user,
                         order_address=order_address,
                         company_data=company_data,
                         invoice_number=invoice_number)

# CRUD de Restaurantes
@app.route('/restaurants')
@login_required
def list_restaurants():
    q = request.args.get('q', '').strip()
    category = request.args.get('category', '').strip()
    min_fee_raw = request.args.get('min_fee', '').strip()
    max_fee_raw = request.args.get('max_fee', '').strip()
    max_time_raw = request.args.get('max_time', '').strip()
    min_rating_raw = request.args.get('min_rating', '').strip()
    favorites_only = request.args.get('favorites', '').strip() == 'true' or request.args.get('favorites_only', '').strip() in ('1','true')
    nearby_flag = request.args.get('nearby', '').strip() == 'true'
    radius_km_raw = request.args.get('radius_km', '').strip()
    user_lat_raw = request.args.get('user_lat', '').strip()
    user_lon_raw = request.args.get('user_lon', '').strip()
    sort_by = request.args.get('sort', 'name')  # name, rating, delivery_time, delivery_fee

    def parse_float(s):
        if not s:
            return None
        try:
            return float(s.replace(',', '.'))
        except (ValueError, TypeError):
            return None

    def parse_int(s):
        if not s:
            return None
        try:
            return int(s)
        except (ValueError, TypeError):
            return None

    # Radius para proximidade
    try:
        radius_km = float(radius_km_raw) if radius_km_raw else 3.0
        if radius_km <= 0:
            radius_km = 3.0
    except (ValueError, TypeError):
        radius_km = 3.0
    user_lat = parse_float(user_lat_raw)
    user_lon = parse_float(user_lon_raw)
    if user_lat is not None and user_lon is not None:
        session['user_lat'] = user_lat
        session['user_lon'] = user_lon

    query = Restaurant.query
    
    # Filtro de favoritos
    if favorites_only:
        favorite_ids = db.session.query(RestaurantFavorite.restaurant_id).filter_by(user_id=current_user.id).subquery()
        query = query.filter(Restaurant.id.in_(favorite_ids))
    
    # Filtros existentes
    if q:
        query = query.filter(
            (Restaurant.name.ilike(f'%{q}%')) |
            (Restaurant.category.ilike(f'%{q}%')) |
            (Restaurant.address.ilike(f'%{q}%'))
        )
    if category:
        query = query.filter(Restaurant.category == category)

    min_fee = parse_float(min_fee_raw)
    max_fee = parse_float(max_fee_raw)
    if min_fee is not None:
        query = query.filter(Restaurant.delivery_fee >= min_fee)
    if max_fee is not None:
        query = query.filter(Restaurant.delivery_fee <= max_fee)

    max_time = parse_int(max_time_raw)
    if max_time is not None:
        query = query.filter(Restaurant.delivery_time <= max_time)

    min_rating = parse_float(min_rating_raw)
    if min_rating is not None:
        query = query.filter(Restaurant.rating >= min_rating)

    # Ordenação
    if sort_by == 'rating':
        query = query.order_by(Restaurant.rating.desc())
    elif sort_by == 'delivery_time':
        query = query.order_by(Restaurant.delivery_time.asc())
    elif sort_by == 'delivery_fee':
        query = query.order_by(Restaurant.delivery_fee.asc())
    else:  # name
        query = query.order_by(Restaurant.name.asc())

    restaurants = query.all()

    # Aplica filtro "Próximos a mim" usando geocodificação do endereço padrão do usuário
    if nearby_flag:
        user_coords = None
        if user_lat is not None and user_lon is not None:
            user_coords = (user_lat, user_lon)
        elif session.get('user_lat') is not None and session.get('user_lon') is not None:
            user_coords = (session.get('user_lat'), session.get('user_lon'))
        elif current_user.is_authenticated:
            default_address = UserAddress.query.filter_by(user_id=current_user.id, is_default=True).first()
            if not default_address:
                default_address = UserAddress.query.filter_by(user_id=current_user.id).first()
            if default_address:
                full_addr = f"{default_address.street}, {default_address.number} - {default_address.neighborhood}, {default_address.city} - {default_address.state}, {default_address.zip_code}, Brasil"
                user_coords = geocode_address(full_addr)
        if user_coords:
            u_lat, u_lon = user_coords
            nearby_list = []
            for r in restaurants:
                r_coords = get_restaurant_coords(r)
                if not r_coords:
                    continue
                r_lat, r_lon = r_coords
                dist_km = haversine_km(u_lat, u_lon, r_lat, r_lon)
                if dist_km <= radius_km:
                    nearby_list.append(r)
            restaurants = nearby_list
    
    # Obter IDs dos restaurantes favoritos do usuário atual
    user_favorites = set()
    if current_user.is_authenticated:
        user_favorites = set(
            fav.restaurant_id for fav in 
            RestaurantFavorite.query.filter_by(user_id=current_user.id).all()
        )
    
    categories = [row[0] for row in db.session.query(Restaurant.category).distinct().order_by(Restaurant.category).all()]

    tmpl_user_lat = user_lat_raw or (str(session.get('user_lat')) if session.get('user_lat') is not None else '')
    tmpl_user_lon = user_lon_raw or (str(session.get('user_lon')) if session.get('user_lon') is not None else '')
    return render_template(
        'restaurants.html',
        restaurants=restaurants,
        q=q,
        categories=categories,
        selected_category=category,
        min_fee=min_fee_raw,
        max_fee=max_fee_raw,
        max_time=max_time_raw,
        min_rating=min_rating_raw,
        favorites_only=favorites_only,
        sort_by=sort_by,
        nearby=nearby_flag,
        radius_km=radius_km,
        user_favorites=user_favorites,
        user_lat=tmpl_user_lat,
        user_lon=tmpl_user_lon,
        user_accuracy=str(session.get('user_accuracy') or '')
    )

@app.route('/restaurants/new', methods=['GET', 'POST'])
@login_required
def create_restaurant():
    if not current_user.is_restaurant:
        current_user.is_restaurant = True
        db.session.commit()
        flash('Sua conta foi convertida para restaurante. Preencha os dados do seu restaurante.', 'info')
        
    if request.method == 'POST':
        try:
            name = (request.form.get('name') or '').strip()
            description = (request.form.get('description') or '').strip()
            address = (request.form.get('address') or '').strip()
            phone = (request.form.get('phone') or '').strip()
            image_url = (request.form.get('image_url') or '').strip()
            category = (request.form.get('category') or '').strip()
            if not name or not address:
                flash('Informe nome e endereço do restaurante.', 'warning')
                return render_template('restaurant_form.html')
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
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao criar restaurante: {str(e)}', 'danger')
            return render_template('restaurant_form.html')
        
    return render_template('restaurant_form.html')

@app.route('/restaurants/<int:restaurant_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_restaurant(restaurant_id):
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    
    # Verificar se o usuário é o proprietário
    if not current_user.is_admin and not (restaurant.owner_id == current_user.id or current_user.is_restaurant):
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

# API JSON para CRUD de Restaurantes (suporta Mobile)
@app.route('/api/restaurants', methods=['GET'])
def api_list_restaurants():
    restaurants = Restaurant.query.all()
    data = []
    for r in restaurants:
        data.append({
            'id': r.id,
            'owner_id': r.owner_id,
            'name': r.name,
            'description': r.description,
            'category': r.category,
            'delivery_fee': r.delivery_fee,
            'delivery_time': r.delivery_time,
            'rating': r.rating,
            'logo': r.logo,
            'address': r.address,
            'phone': r.phone,
            'image_url': r.image_url,
        })
    return jsonify(data)

@app.route('/api/restaurants', methods=['POST'])
def api_create_restaurant():
    payload = request.get_json(force=True, silent=True) or {}
    required = ['owner_id', 'name', 'address']
    for field in required:
        if not payload.get(field):
            return jsonify({'error': f'Campo obrigatório ausente: {field}'}), 400
    r = Restaurant(
        owner_id=payload['owner_id'],
        name=payload['name'],
        description=payload.get('description'),
        category=payload.get('category'),
        delivery_fee=payload.get('delivery_fee', 0.0),
        delivery_time=payload.get('delivery_time'),
        rating=payload.get('rating', 0.0),
        logo=payload.get('logo'),
        address=payload['address'],
        phone=payload.get('phone'),
        image_url=payload.get('image_url'),
    )
    db.session.add(r)
    db.session.commit()
    return jsonify({'id': r.id}), 201

@app.route('/api/restaurants/<int:restaurant_id>', methods=['PUT'])
def api_update_restaurant(restaurant_id):
    r = Restaurant.query.get_or_404(restaurant_id)
    payload = request.get_json(force=True, silent=True) or {}
    for field in ['name','description','category','delivery_fee','delivery_time','rating','logo','address','phone','image_url']:
        if field in payload:
            setattr(r, field, payload[field])
    db.session.commit()
    return jsonify({'status': 'ok'})

@app.route('/api/restaurants/<int:restaurant_id>', methods=['DELETE'])
def api_delete_restaurant(restaurant_id):
    r = Restaurant.query.get_or_404(restaurant_id)
    db.session.delete(r)
    db.session.commit()
    return jsonify({'status': 'deleted'})

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
        # Parse preço aceitando vírgula
        price_raw = request.form.get('price', '').strip()
        try:
            price = float(price_raw.replace(',', '.'))
        except (ValueError, TypeError):
            flash('Preço inválido. Use números como 39,90 ou 39.90.', 'danger')
            return render_template('menu_item_form.html', restaurant=restaurant)
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
        # Parse preço aceitando vírgula
        price_raw = request.form.get('price', '').strip()
        try:
            menu_item.price = float(price_raw.replace(',', '.'))
        except (ValueError, TypeError):
            flash('Preço inválido. Use números como 39,90 ou 39.90.', 'danger')
            return render_template('menu_item_form.html', restaurant=restaurant, menu_item=menu_item)
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

# CRUD de Endereços do Usuário
@app.route('/addresses')
@login_required
def list_addresses():
    addresses = UserAddress.query.filter_by(user_id=current_user.id).order_by(UserAddress.is_default.desc(), UserAddress.created_at.desc()).all()
    return render_template('addresses.html', addresses=addresses)

@app.route('/addresses/new', methods=['GET', 'POST'])
@login_required
def create_address():
    if request.method == 'POST':
        form = {k: (request.form.get(k) or '').strip() for k in ['name','street','number','complement','neighborhood','city','state','zip_code','reference']}
        required_fields = ['name','street','number','neighborhood','city','state','zip_code']
        missing = [f for f in required_fields if not form.get(f)]
        if missing:
            flash('Preencha todos os campos obrigatórios: ' + ', '.join(missing), 'danger')
            return render_template('address_form.html', address=form)
        is_first_address = UserAddress.query.filter_by(user_id=current_user.id).count() == 0
        is_default = (request.form.get('is_default') == 'on') or is_first_address
        if is_default:
            UserAddress.query.filter_by(user_id=current_user.id, is_default=True).update({'is_default': False})
        try:
            address = UserAddress(
                user_id=current_user.id,
                name=form['name'],
                street=form['street'],
                number=form['number'],
                complement=form['complement'],
                neighborhood=form['neighborhood'],
                city=form['city'],
                state=form['state'],
                zip_code=form['zip_code'],
                reference=form['reference'],
                is_default=is_default
            )
            db.session.add(address)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash('Erro ao salvar endereço: ' + str(e), 'danger')
            return render_template('address_form.html', address=form)
        flash('Endereço adicionado com sucesso!', 'success')
        return redirect(url_for('list_addresses'))
    return render_template('address_form.html')

@app.route('/addresses/<int:address_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_address(address_id):
    address = UserAddress.query.get_or_404(address_id)
    
    # Verificar se o endereço pertence ao usuário atual
    if address.user_id != current_user.id:
        flash('Você não tem permissão para editar este endereço.', 'danger')
        return redirect(url_for('list_addresses'))
    
    if request.method == 'POST':
        is_default = request.form.get('is_default') == 'on'
        
        # Se marcado como padrão, desmarcar outros endereços
        if is_default and not address.is_default:
            UserAddress.query.filter_by(user_id=current_user.id, is_default=True).update({'is_default': False})
        
        address.name = request.form.get('name')
        address.street = request.form.get('street')
        address.number = request.form.get('number')
        address.complement = request.form.get('complement')
        address.neighborhood = request.form.get('neighborhood')
        address.city = request.form.get('city')
        address.state = request.form.get('state')
        address.zip_code = request.form.get('zip_code')
        address.reference = request.form.get('reference')
        address.is_default = is_default
        
        db.session.commit()
        
        flash('Endereço atualizado com sucesso!', 'success')
        return redirect(url_for('list_addresses'))
    
    return render_template('address_form.html', address=address)

@app.route('/addresses/<int:address_id>/delete', methods=['POST'])
@login_required
def delete_address(address_id):
    address = UserAddress.query.get_or_404(address_id)
    
    # Verificar se o endereço pertence ao usuário atual
    if address.user_id != current_user.id:
        flash('Você não tem permissão para excluir este endereço.', 'danger')
        return redirect(url_for('list_addresses'))
    
    # Se for o endereço padrão, definir outro como padrão
    if address.is_default:
        other_address = UserAddress.query.filter_by(user_id=current_user.id).filter(UserAddress.id != address_id).first()
        if other_address:
            other_address.is_default = True
    
    db.session.delete(address)
    db.session.commit()
    
    flash('Endereço excluído com sucesso!', 'success')
    return redirect(url_for('list_addresses'))

@app.route('/addresses/<int:address_id>/set-default', methods=['POST'])
@login_required
def set_default_address(address_id):
    address = UserAddress.query.get_or_404(address_id)
    
    # Verificar se o endereço pertence ao usuário atual
    if address.user_id != current_user.id:
        flash('Você não tem permissão para modificar este endereço.', 'danger')
        return redirect(url_for('list_addresses'))
    
    # Desmarcar todos os endereços como padrão
    UserAddress.query.filter_by(user_id=current_user.id, is_default=True).update({'is_default': False})
    
    # Marcar este endereço como padrão
    address.is_default = True
    db.session.commit()
    
    flash('Endereço definido como padrão!', 'success')
    return redirect(url_for('list_addresses'))

# CRUD de Usuários
@app.route('/users')
@login_required
def list_users():
    if not current_user.is_admin:
        return redirect(url_for('index'))
    users = User.query.all()
    return render_template('users.html', users=users)

@app.route('/users/<int:user_id>')
@login_required
def view_user(user_id):
    if current_user.id != user_id and not current_user.is_admin:
        return redirect(url_for('index'))
    user = User.query.get_or_404(user_id)
    return render_template('user_detail.html', user=user)

@app.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    if current_user.id != user_id and not current_user.is_admin:
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
    if current_user.id != user_id and not current_user.is_admin:
        return redirect(url_for('index'))

    user = User.query.get_or_404(user_id)

    try:
        # Excluir restaurantes do usuário e dados relacionados
        restaurants = Restaurant.query.filter_by(owner_id=user.id).all()
        for r in restaurants:
            # Excluir pedidos desse restaurante (de qualquer cliente)
            orders_for_restaurant = Order.query.filter_by(restaurant_id=r.id).all()
            for o in orders_for_restaurant:
                OrderItem.query.filter_by(order_id=o.id).delete()
                db.session.delete(o)

            # Excluir itens do cardápio
            MenuItem.query.filter_by(restaurant_id=r.id).delete()

            # Excluir o restaurante
            db.session.delete(r)

        # Excluir pedidos realizados pelo usuário
        user_orders = Order.query.filter_by(user_id=user.id).all()
        for o in user_orders:
            OrderItem.query.filter_by(order_id=o.id).delete()
            db.session.delete(o)

        # Excluir vinculações de OAuth (se existirem)
        try:
            OAuth.query.filter_by(user_id=user.id).delete()
        except Exception:
            pass

        # Finalmente, excluir o usuário
        db.session.delete(user)
        db.session.commit()
    except Exception:
        db.session.rollback()
        flash('Falha ao excluir a conta. Por favor, tente novamente.', 'danger')
        return redirect(url_for('view_user', user_id=user_id))

    if current_user.is_authenticated and current_user.id == user_id:
        logout_user()
        flash('Sua conta foi excluída com sucesso!', 'success')
        return redirect(url_for('index'))

    flash('Usuário excluído com sucesso!', 'success')
    return redirect(url_for('list_users'))


@app.route('/restaurants/<int:restaurant_id>/favorite', methods=['POST'])
@login_required
def favorite_restaurant(restaurant_id):
    """Adicionar restaurante aos favoritos"""
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    
    # Verificar se já está nos favoritos
    existing_favorite = RestaurantFavorite.query.filter_by(
        user_id=current_user.id,
        restaurant_id=restaurant_id
    ).first()
    
    if existing_favorite:
        return jsonify({'success': False, 'message': 'Restaurante já está nos favoritos'})
    
    # Adicionar aos favoritos
    favorite = RestaurantFavorite(
        user_id=current_user.id,
        restaurant_id=restaurant_id
    )
    
    try:
        db.session.add(favorite)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Restaurante adicionado aos favoritos'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Erro ao favoritar: {str(e)}'})


@app.route('/restaurants/<int:restaurant_id>/unfavorite', methods=['POST'])
@login_required
def unfavorite_restaurant(restaurant_id):
    """Remover restaurante dos favoritos"""
    favorite = RestaurantFavorite.query.filter_by(
        user_id=current_user.id,
        restaurant_id=restaurant_id
    ).first()
    
    if not favorite:
        return jsonify({'success': False, 'message': 'Restaurante não está nos favoritos'})
    
    try:
        db.session.delete(favorite)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Restaurante removido dos favoritos'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Erro ao desfavoritar: {str(e)}'})


@app.route('/favorites')
@login_required
def list_favorites():
    """Listar restaurantes favoritos do usuário"""
    favorites = db.session.query(Restaurant).join(RestaurantFavorite).filter(
        RestaurantFavorite.user_id == current_user.id
    ).all()
    
    return render_template('favorites.html', restaurants=favorites)


# Inicialização resiliente do banco de dados
with app.app_context():
    # Tenta criar as tabelas conforme os modelos definidos, separando por bind
    try:
        users_tables = [User.__table__, OAuth.__table__, UserAddress.__table__]
        db.Model.metadata.create_all(bind=db.engine, tables=users_tables)
        rest_engine = db.get_engine(app, bind='restaurants')
        rest_tables = [
            Restaurant.__table__, MenuItem.__table__,
            Cart.__table__, CartItem.__table__,
            Order.__table__, OrderItem.__table__,
            RestaurantFavorite.__table__, ProductFavorite.__table__,
            RestaurantGeo.__table__
        ]
        db.Model.metadata.create_all(bind=rest_engine, tables=rest_tables)
    except Exception:
        pass
    try:
        # Seed de dados de demonstração para facilitar testes em uma instalação limpa
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
                image_url='/static/images/restaurant-bg.jpg'
            )
            db.session.add(demo_restaurant)
            db.session.commit()

            demo_item = MenuItem(
                restaurant_id=demo_restaurant.id,
                name='Pizza Margherita',
                description='Clássica com tomate, mozzarella e manjericão',
                price=39.90,
                image_url='/static/images/food-placeholder.jpg',
                category='Pizza',
                available=True
            )
            db.session.add(demo_item)
            db.session.commit()
    except Exception:
        # Em caso de incompatibilidade de esquema (ex.: migração de colunas para português), força recriação
        try:
            db.drop_all()
            db.drop_all(bind='restaurants')
        except Exception:
            pass
        try:
            users_tables = [User.__table__, OAuth.__table__, UserAddress.__table__]
            db.Model.metadata.create_all(bind=db.engine, tables=users_tables)
            rest_engine = db.get_engine(app, bind='restaurants')
            rest_tables = [
                Restaurant.__table__, MenuItem.__table__,
                Cart.__table__, CartItem.__table__,
                Order.__table__, OrderItem.__table__,
                RestaurantFavorite.__table__, ProductFavorite.__table__,
                RestaurantGeo.__table__
            ]
            db.Model.metadata.create_all(bind=rest_engine, tables=rest_tables)
        except Exception:
            pass

@app.route('/products')
def list_products():
    """Lista global de produtos (itens de menu) com filtros e opção 'Próximos a mim'."""
    q = request.args.get('q', '').strip()
    category = request.args.get('category', '').strip()
    available_only = request.args.get('available', '').strip() == 'true'
    min_price_raw = request.args.get('min_price', '').strip()
    max_price_raw = request.args.get('max_price', '').strip()
    sort_by = request.args.get('sort', 'name')  # name, price_asc, price_desc
    nearby_flag = request.args.get('nearby', '').strip() == 'true'
    favorites_only = request.args.get('favorites', '').strip() == 'true' or request.args.get('favorites_only', '').strip() in ('1','true')
    radius_km_raw = request.args.get('radius_km', '').strip()
    user_lat_raw = request.args.get('user_lat', '').strip()
    user_lon_raw = request.args.get('user_lon', '').strip()

    # Parse de valores numéricos
    min_price = parse_float(min_price_raw)
    max_price = parse_float(max_price_raw)
    try:
        radius_km = float(radius_km_raw) if radius_km_raw else 3.0
        if radius_km <= 0:
            radius_km = 3.0
    except (ValueError, TypeError):
        radius_km = 3.0
    user_lat = parse_float(user_lat_raw)
    user_lon = parse_float(user_lon_raw)
    if user_lat is not None and user_lon is not None:
        session['user_lat'] = user_lat
        session['user_lon'] = user_lon

    # Query base: join com restaurante para permitir busca por nome do restaurante
    query = db.session.query(MenuItem, Restaurant).join(Restaurant, MenuItem.restaurant_id == Restaurant.id)

    # Filtros de texto e categoria
    if q:
        like_q = f"%{q}%"
        query = query.filter(
            (MenuItem.name.ilike(like_q)) |
            (MenuItem.description.ilike(like_q)) |
            (Restaurant.name.ilike(like_q)) |
            (Restaurant.category.ilike(like_q))
        )
    if category:
        query = query.filter(MenuItem.category == category)

    # Filtros de preço e disponibilidade
    if min_price is not None:
        query = query.filter(MenuItem.price >= min_price)
    if max_price is not None:
        query = query.filter(MenuItem.price <= max_price)
    if available_only:
        query = query.filter(MenuItem.available == True)

    # Ordenação
    if sort_by == 'price_asc':
        query = query.order_by(MenuItem.price.asc())
    elif sort_by == 'price_desc':
        query = query.order_by(MenuItem.price.desc())
    else:  # name
        query = query.order_by(MenuItem.name.asc())

    # Filtro de favoritos (se solicitado e usuário autenticado)
    user_favorite_item_ids = set()
    if current_user.is_authenticated:
        user_favorite_item_ids = set(
            fav.menu_item_id for fav in ProductFavorite.query.filter_by(user_id=current_user.id).all()
        )
        if favorites_only:
            if user_favorite_item_ids:
                query = query.filter(MenuItem.id.in_(user_favorite_item_ids))
            else:
                # Nenhum favorito — resultado vazio
                return render_template(
                    'products.html',
                    items=[],
                    q=q,
                    categories=[row[0] for row in db.session.query(MenuItem.category).distinct().order_by(MenuItem.category).all() if row[0]],
                    selected_category=category,
                    min_price=min_price_raw,
                    max_price=max_price_raw,
                    available_only=available_only,
                    sort_by=sort_by,
                    nearby=nearby_flag,
                    radius_km=radius_km,
                    favorites_only=favorites_only,
                    user_favorite_item_ids=user_favorite_item_ids,
                    user_lat=user_lat_raw,
                    user_lon=user_lon_raw
                )

    if favorites_only and not current_user.is_authenticated:
        return render_template(
            'products.html',
            items=[],
            q=q,
            categories=[row[0] for row in db.session.query(MenuItem.category).distinct().order_by(MenuItem.category).all() if row[0]],
            selected_category=category,
            min_price=min_price_raw,
            max_price=max_price_raw,
            available_only=available_only,
            sort_by=sort_by,
            nearby=nearby_flag,
            radius_km=radius_km,
            favorites_only=favorites_only,
            user_favorite_item_ids=[],
            user_lat=user_lat_raw,
            user_lon=user_lon_raw
        )

    results = query.all()

    # Proximidade: geocodificar endereço padrão do usuário e filtrar por raio
    items_data = []
    user_coords = None
    if nearby_flag:
        if user_lat is not None and user_lon is not None:
            user_coords = (user_lat, user_lon)
        elif session.get('user_lat') is not None and session.get('user_lon') is not None:
            user_coords = (session.get('user_lat'), session.get('user_lon'))
        elif current_user.is_authenticated:
            default_address = UserAddress.query.filter_by(user_id=current_user.id, is_default=True).first()
            if not default_address:
                default_address = UserAddress.query.filter_by(user_id=current_user.id).first()
            if default_address:
                full_addr = f"{default_address.street}, {default_address.number} - {default_address.neighborhood}, {default_address.city} - {default_address.state}, {default_address.zip_code}, Brasil"
                user_coords = geocode_address(full_addr)

    for item, restaurant in results:
        distance_km = None
        if user_coords and restaurant.address:
            r_coords = get_restaurant_coords(restaurant)
            if r_coords:
                distance_km = haversine_km(user_coords[0], user_coords[1], r_coords[0], r_coords[1])
        # Se proximidade está ativada, filtra pelo raio
        if nearby_flag and user_coords is not None:
            if distance_km is None or distance_km > radius_km:
                continue
        items_data.append({
            'item': item,
            'restaurant': restaurant,
            'distance_km': distance_km
        })

    # Categorias distintas para chips/filtros
    item_categories = [row[0] for row in db.session.query(MenuItem.category).distinct().order_by(MenuItem.category).all() if row[0]]

    tmpl_user_lat = user_lat_raw or (str(session.get('user_lat')) if session.get('user_lat') is not None else '')
    tmpl_user_lon = user_lon_raw or (str(session.get('user_lon')) if session.get('user_lon') is not None else '')
    return render_template(
        'products.html',
        items=items_data,
        q=q,
        categories=item_categories,
        selected_category=category,
        min_price=min_price_raw,
        max_price=max_price_raw,
        available_only=available_only,
        sort_by=sort_by,
        nearby=nearby_flag,
        radius_km=radius_km,
        favorites_only=favorites_only,
        user_favorite_item_ids=user_favorite_item_ids,
        user_lat=tmpl_user_lat,
        user_lon=tmpl_user_lon,
        user_accuracy=str(session.get('user_accuracy') or '')
    )

@app.route('/products/<int:item_id>/favorite', methods=['POST'])
@login_required
def favorite_item(item_id):
    menu_item = MenuItem.query.get_or_404(item_id)
    existing = ProductFavorite.query.filter_by(user_id=current_user.id, menu_item_id=item_id).first()
    if existing:
        return jsonify({'success': False, 'message': 'Produto já está nos favoritos'})
    fav = ProductFavorite(user_id=current_user.id, menu_item_id=item_id)
    try:
        db.session.add(fav)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Produto adicionado aos favoritos'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Erro ao favoritar: {str(e)}'})

@app.route('/products/<int:item_id>/unfavorite', methods=['POST'])
@login_required
def unfavorite_item(item_id):
    fav = ProductFavorite.query.filter_by(user_id=current_user.id, menu_item_id=item_id).first()
    if not fav:
        return jsonify({'success': False, 'message': 'Produto não está nos favoritos'})
    try:
        db.session.delete(fav)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Produto removido dos favoritos'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Erro ao remover favorito: {str(e)}'})

# Rota de diagnóstico para verificar persistência e caminho do banco
@app.route('/debug/db-info')
def debug_db_info():
    uri = app.config.get('SQLALCHEMY_DATABASE_URI')
    # Caminhos dos bancos
    try:
        users_db = db.engine.url.database
    except Exception:
        users_db = None
    try:
        restaurants_engine = db.get_engine(app, bind='restaurants')
        restaurants_db = restaurants_engine.url.database
    except Exception:
        restaurants_db = None
    users_db_path = os.path.abspath(users_db) if users_db and not os.path.isabs(users_db) else users_db
    restaurants_db_path = os.path.abspath(restaurants_db) if restaurants_db and not os.path.isabs(restaurants_db) else restaurants_db
    counts = {
        'users': User.query.count(),
        'restaurants': Restaurant.query.count(),
        'menu_items': MenuItem.query.count(),
        'orders': Order.query.count(),
        'order_items': OrderItem.query.count()
    }
    return jsonify({'ok': True, 'uri': uri, 'db_users_path': users_db_path, 'db_restaurants_path': restaurants_db_path, 'counts': counts})

@app.route('/debug/backfill-restaurant-geo', methods=['POST'])
@app.route('/debug/backfill_restaurant_geo', methods=['POST'])
def debug_backfill_restaurant_geo():
    try:
        updated = 0
        for r in Restaurant.query.all():
            if not r.address:
                continue
            rec = RestaurantGeo.query.filter_by(restaurant_id=r.id).first()
            if rec:
                continue
            coords = geocode_address(r.address)
            if not coords:
                continue
            lat, lon = coords
            db.session.add(RestaurantGeo(restaurant_id=r.id, lat=lat, lon=lon))
            updated += 1
        db.session.commit()
        return jsonify({'ok': True, 'updated': updated})
    except Exception as e:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(e)})

@app.route('/api/db-counts')
def api_db_counts():
    counts = {
        'users': User.query.count(),
        'restaurants': Restaurant.query.count(),
        'menu_items': MenuItem.query.count(),
        'orders': Order.query.count(),
        'order_items': OrderItem.query.count()
    }
    return jsonify({'ok': True, 'counts': counts})

# Ferramentas para apresentação: resetar banco e popular dados demo
@app.route('/debug/reset-db', methods=['POST'])
def debug_reset_db():
    users_db = db.engine.url.database
    restaurants_engine = db.get_engine(app, bind='restaurants')
    restaurants_db = restaurants_engine.url.database if restaurants_engine else None
    # Remover bancos
    for path in [users_db, restaurants_db]:
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass
    # Recriar esquemas separando por bind
    try:
        users_tables = [User.__table__, OAuth.__table__, UserAddress.__table__]
        db.Model.metadata.create_all(bind=db.engine, tables=users_tables)
        rest_engine = db.get_engine(app, bind='restaurants')
        rest_tables = [
            Restaurant.__table__, MenuItem.__table__,
            Cart.__table__, CartItem.__table__,
            Order.__table__, OrderItem.__table__,
            RestaurantFavorite.__table__, ProductFavorite.__table__
        ]
        db.Model.metadata.create_all(bind=rest_engine, tables=rest_tables)
    except Exception:
        pass
    return jsonify({'status': 'ok', 'message': 'Bancos resetados e recriados.'})

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
            image_url='/static/images/restaurant-bg.jpg'
        )
        db.session.add(demo_restaurant)
        db.session.commit()

        demo_item = MenuItem(
            restaurant_id=demo_restaurant.id,
            name='Pizza Margherita',
            description='Clássica com tomate, mozzarella e manjericão',
            price=39.90,
            image_url='/static/images/food-placeholder.jpg',
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

@app.route('/debug/seed-many', methods=['POST'])
def debug_seed_many():
    owner = User.query.filter_by(is_restaurant=True).first()
    if not owner:
        owner = User(name='Seed Owner', email='seed@restaurant.com', is_restaurant=True)
        db.session.add(owner)
        db.session.commit()
    categories = ['Pizza','Burger','Sushi','Pastel','Salada','Massa','Churrasco','Arabe','Doces','Vegano']
    names = [
        'Cantina Italia','Burger House','Sushi Prime','Pastelaria da Feira','Green Salad','Massas & Cia',
        'Churras Bom','Sabores Arabes','Doceria Fina','Vegano & Leve'
    ]
    sp_addresses = [
        'Avenida Paulista, 1000 - Bela Vista, São Paulo - SP, 01310-100',
        'Rua Oscar Freire, 900 - Jardins, São Paulo - SP, 01426-001',
        'Rua Augusta, 1500 - Consolação, São Paulo - SP, 01305-100',
        'Rua Haddock Lobo, 595 - Cerqueira César, São Paulo - SP, 01414-001',
        'Rua dos Pinheiros, 1308 - Pinheiros, São Paulo - SP, 05422-002',
        'Avenida Brigadeiro Faria Lima, 2232 - Itaim Bibi, São Paulo - SP, 01451-000',
        'Avenida Ibirapuera, 3100 - Moema, São Paulo - SP, 04028-002',
        'Avenida Ipiranga, 200 - República, São Paulo - SP, 01046-925',
        'Rua Domingos de Morais, 2564 - Vila Mariana, São Paulo - SP, 04010-100',
        'Avenida Engenheiro Luís Carlos Berrini, 105 - Brooklin, São Paulo - SP, 04571-010'
    ]
    catalog = {
        'Pizza': ['Margherita','Calabresa','Quatro Queijos','Pepperoni','Portuguesa','Frango com Catupiry','Napolitana','Baiana'],
        'Burger': ['Cheddar Supreme','Duplo Bacon','Veggie Grill','BBQ Smokehouse','Crispy Chicken','Blue Cheese Burger'],
        'Sushi': ['Temaki Salmão','Uramaki Califórnia','Sashimi Salmão','Hot Roll','Nigiri Atum','Gunkan Ikura'],
        'Pastel': ['Carne','Queijo','Frango com Catupiry','Palmito','Pizza','Calabresa com Queijo'],
        'Salada': ['Caesar','Grega','Tropical','Caprese','Quinoa e Vegetais','Salada de Grão-de-bico'],
        'Massa': ['Spaghetti Carbonara','Fettuccine Alfredo','Penne ao Pesto','Lasanha Bolonhesa','Ravioli de Ricota','Gnocchi ao Sugo'],
        'Churrasco': ['Picanha','Maminha','Fraldinha','Costela ao Barbecue','Linguiça Artesanal','Cupim'],
        'Arabe': ['Kibe Assado','Esfiha de Carne','Tabule','Falafel','Homus com Pão Sírio','Babaganoush'],
        'Doces': ['Brigadeiro Gourmet','Cheesecake Frutas Vermelhas','Brownie com Sorvete','Pudim de Leite','Tiramisu','Banoffee'],
        'Vegano': ['Bowl de Grãos','Hambúrguer de Grão-de-bico','Tofu Grelhado','Ratatouille','Curry de Legumes','Falafel Wrap']
    }
    for i, name in enumerate(names):
        cat = categories[i % len(categories)]
        existing = Restaurant.query.filter_by(name=name).first()
        if not existing:
            r = Restaurant(owner_id=owner.id, name=name, description=f'{cat} especial', category=cat,
                           delivery_fee=5.0 + i, delivery_time=20 + i, rating=4.0, address=sp_addresses[i % len(sp_addresses)])
            db.session.add(r)
            db.session.commit()
            lst = catalog.get(cat, [])
            shift = i % (len(lst) or 1)
            pick = (lst[shift:] + lst[:shift])[:5] if lst else [f'{cat} {k+1}' for k in range(5)]
            for j, item_name in enumerate(pick):
                price = round(20.0 + j*5 + i, 2)
                mi = MenuItem(restaurant_id=r.id, name=item_name, description=f'{item_name} preparado na hora',
                              price=price, image_url='/static/images/food-placeholder.jpg', category=cat, available=True)
                db.session.add(mi)
            db.session.commit()
        else:
            import re
            lst = catalog.get(cat, [])
            if lst:
                shift = i % (len(lst) or 1)
                target = (lst[shift:] + lst[:shift])
                gen_items = MenuItem.query.filter_by(restaurant_id=existing.id, category=cat).order_by(MenuItem.id.asc()).all()
                to_update = [mi for mi in gen_items if re.fullmatch(fr'{cat} \d+', mi.name)]
                for idx, mi in enumerate(to_update):
                    if idx < len(target):
                        mi.name = target[idx]
                        if not mi.description:
                            mi.description = f'{mi.name} preparado na hora'
                db.session.commit()
            if existing.address and existing.address.startswith('Rua ') and name in existing.address:
                existing.address = sp_addresses[i % len(sp_addresses)]
                db.session.commit()
    demo = Restaurant.query.filter_by(name='Pizzaria Demo').first()
    target_restaurant_id = demo.id if demo else Restaurant.query.first().id
    extra_items = [
        ('Pizza Calabresa','Pizza',44.90),
        ('Burger Cheddar','Burger',29.90),
        ('Temaki Salmão','Sushi',34.90),
        ('Pastel de Carne','Pastel',12.00),
        ('Salada Caesar','Salada',24.50)
    ]
    for nm, cat, pr in extra_items:
        exists_item = MenuItem.query.filter_by(name=nm, restaurant_id=target_restaurant_id).first()
        if not exists_item:
            db.session.add(MenuItem(restaurant_id=target_restaurant_id, name=nm, description=f'{nm} feito na hora',
                                    price=pr, image_url='/static/images/food-placeholder.jpg', category=cat, available=True))
    db.session.commit()
    counts = {
        'users': User.query.count(),
        'restaurants': Restaurant.query.count(),
        'menu_items': MenuItem.query.count(),
        'orders': Order.query.count(),
        'order_items': OrderItem.query.count()
    }
    return jsonify({'status':'ok','counts':counts})

@app.route('/debug/claim-restaurants', methods=['POST'])
@login_required
def debug_claim_restaurants():
    try:
        # Garante que o usuário atual é marcado como conta de restaurante
        if not current_user.is_restaurant:
            current_user.is_restaurant = True
            db.session.commit()
        # Reatribui todos os restaurantes ao usuário atual
        for r in Restaurant.query.all():
            r.owner_id = current_user.id
        db.session.commit()
        return jsonify({'ok': True, 'message': 'Restaurantes agora pertencem ao usuário atual', 'owner_id': current_user.id, 'restaurants': Restaurant.query.count()})
    except Exception as e:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(e)})

@app.route('/debug/make-me-restaurant', methods=['POST'])
@login_required
def debug_make_me_restaurant():
    try:
        current_user.is_restaurant = True
        db.session.commit()
        return jsonify({'ok': True, 'user_id': current_user.id, 'is_restaurant': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(e)})

@app.route('/debug/fix-images', methods=['POST'])
def debug_fix_images():
    try:
        updated = 0
        for mi in MenuItem.query.filter(MenuItem.image_url.like('https://via.placeholder.com/%')).all():
            mi.image_url = '/static/images/food-placeholder.jpg'
            updated += 1
        for r in Restaurant.query.filter(Restaurant.image_url.like('https://via.placeholder.com/%')).all():
            r.image_url = '/static/images/restaurant-bg.jpg'
            updated += 1
        db.session.commit()
        return jsonify({'ok': True, 'updated': updated})
    except Exception as e:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(e)})

if __name__ == '__main__':
    ssl_ctx = 'adhoc' if str(os.environ.get('USE_HTTPS_DEV', '')).strip().lower() in ('1','true','yes','on') else None
    app.run(host='127.0.0.1', port=int(os.environ.get('PORT', 5000)), debug=True, use_reloader=False, ssl_context=ssl_ctx)
@app.route('/account/disconnect-google', methods=['POST'])
@login_required
def disconnect_google():
    try:
        if OAUTH_AVAILABLE:
            try:
                google_bp.storage.set(None)
            except Exception:
                pass
        session.pop('google_oauth_token', None)
        session.pop('google_oauth_state', None)
        user = User.query.get(current_user.id)
        if user:
            user.social_id = None
            user.social_provider = None
            db.session.commit()
        flash('Conta Google desvinculada com sucesso.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao desvincular Google: {str(e)}', 'danger')
    return redirect(url_for('profile')) if hasattr(current_user, 'id') else redirect(url_for('login'))

@app.route('/account/delete', methods=['POST'])
@login_required
def delete_account():
    try:
        uid = current_user.id
        # Remover tokens OAuth
        try:
            if OAUTH_AVAILABLE:
                google_bp.storage.set(None)
            for tok in OAuth.query.filter_by(user_id=uid).all():
                db.session.delete(tok)
        except Exception:
            pass
        # Remover favoritos
        for rf in RestaurantFavorite.query.filter_by(user_id=uid).all():
            db.session.delete(rf)
        for pf in ProductFavorite.query.filter_by(user_id=uid).all():
            db.session.delete(pf)
        # Remover carrinhos
        for cart in Cart.query.filter_by(user_id=uid).all():
            for it in CartItem.query.filter_by(cart_id=cart.id).all():
                db.session.delete(it)
            db.session.delete(cart)
        # Remover pedidos
        for order in Order.query.filter_by(user_id=uid).all():
            for it in OrderItem.query.filter_by(order_id=order.id).all():
                db.session.delete(it)
            db.session.delete(order)
        # Remover endereços
        for addr in UserAddress.query.filter_by(user_id=uid).all():
            db.session.delete(addr)
        # Remover restaurantes do usuário
        for r in Restaurant.query.filter_by(owner_id=uid).all():
            for mi in MenuItem.query.filter_by(restaurant_id=r.id).all():
                db.session.delete(mi)
            # Remover favoritos vinculados ao restaurante
            for rf in RestaurantFavorite.query.filter_by(restaurant_id=r.id).all():
                db.session.delete(rf)
            for ci in Cart.query.filter_by(restaurant_id=r.id).all():
                for it in CartItem.query.filter_by(cart_id=ci.id).all():
                    db.session.delete(it)
                db.session.delete(ci)
            for od in Order.query.filter_by(restaurant_id=r.id).all():
                for it in OrderItem.query.filter_by(order_id=od.id).all():
                    db.session.delete(it)
                db.session.delete(od)
            if hasattr(r, 'geo_record') and r.geo_record:
                db.session.delete(r.geo_record)
            db.session.delete(r)
        # Remover usuário
        user = User.query.get(uid)
        if user:
            db.session.delete(user)
        db.session.commit()
        logout_user()
        flash('Sua conta foi excluída com sucesso.', 'success')
        return redirect(url_for('index'))
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir conta: {str(e)}', 'danger')
        return redirect(url_for('profile')) if hasattr(current_user, 'id') else redirect(url_for('login'))
