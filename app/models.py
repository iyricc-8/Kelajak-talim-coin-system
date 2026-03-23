from datetime import datetime
from flask import current_app
from flask_login import UserMixin
from itsdangerous import URLSafeTimedSerializer, BadTimeSignature, SignatureExpired
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(64), nullable=False)
    last_name = db.Column(db.String(64), nullable=False)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(128), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    avatar = db.Column(db.String(256), nullable=True)
    role = db.Column(db.String(20), default='student')  # student, teacher, admin
    is_active = db.Column(db.Boolean, default=True)
    xp = db.Column(db.Integer, default=0)
    level = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    wallet = db.relationship('Wallet', backref='user', uselist=False, lazy=True)
    transactions = db.relationship('Transaction', foreign_keys='Transaction.user_id', backref='user', lazy='dynamic')
    orders = db.relationship('Order', backref='user', lazy='dynamic')
    achievements = db.relationship('UserAchievement', backref='user', lazy='dynamic')
    notifications = db.relationship('Notification', backref='user', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'

    @property
    def coin_balance(self):
        if self.wallet:
            return self.wallet.balance
        return 0

    @property
    def unread_notifications_count(self):
        return self.notifications.filter_by(is_read=False).count()

    def is_admin(self):
        return self.role == 'admin'

    def is_teacher(self):
        return self.role in ('teacher', 'admin')

    def get_reset_token(self, expires_in=None):
        serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        return serializer.dumps({'user_id': self.id}, salt='password-reset')

    @staticmethod
    def verify_reset_token(token, max_age=None):
        serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        max_age = max_age or current_app.config.get('PASSWORD_RESET_TOKEN_EXPIRES', 3600)
        try:
            data = serializer.loads(token, salt='password-reset', max_age=max_age)
        except (BadTimeSignature, SignatureExpired):
            return None
        return User.query.get(data.get('user_id'))

    def __repr__(self):
        return f'<User {self.username}>'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class Wallet(db.Model):
    __tablename__ = 'wallets'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    balance = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f'<Wallet user_id={self.user_id} balance={self.balance}>'


class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # earn, spend, adjustment, penalty
    amount = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(256), nullable=False)
    comment = db.Column(db.Text, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    balance_after = db.Column(db.Integer, nullable=False)

    creator = db.relationship('User', foreign_keys=[created_by], backref='created_transactions')

    def __repr__(self):
        return f'<Transaction {self.type} {self.amount} for user {self.user_id}>'


class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text, nullable=True)

    products = db.relationship('Product', backref='category', lazy='dynamic')

    def __repr__(self):
        return f'<Category {self.name}>'


class Product(db.Model):
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(256), nullable=False)
    description = db.Column(db.Text, nullable=True)
    image = db.Column(db.String(256), nullable=True)
    price_coin = db.Column(db.Integer, nullable=False)
    stock = db.Column(db.Integer, default=0)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    orders = db.relationship('Order', backref='product', lazy='dynamic')

    def __repr__(self):
        return f'<Product {self.title}>'


class Order(db.Model):
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    price_at_purchase = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='new')  # new, confirmed, delivered, cancelled
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Order {self.id} user={self.user_id}>'


class Achievement(db.Model):
    __tablename__ = 'achievements'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(256), nullable=False)
    description = db.Column(db.Text, nullable=True)
    icon = db.Column(db.String(10), default='🏅')
    condition_type = db.Column(db.String(64), nullable=False)
    condition_value = db.Column(db.Integer, nullable=False)
    is_active = db.Column(db.Boolean, default=True)

    user_achievements = db.relationship('UserAchievement', backref='achievement', lazy='dynamic')

    def __repr__(self):
        return f'<Achievement {self.title}>'


class UserAchievement(db.Model):
    __tablename__ = 'user_achievements'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    achievement_id = db.Column(db.Integer, db.ForeignKey('achievements.id'), nullable=False)
    received_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<UserAchievement user={self.user_id} achievement={self.achievement_id}>'


class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(256), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Notification user={self.user_id} read={self.is_read}>'


class EconomySetting(db.Model):
    __tablename__ = 'economy_settings'

    id = db.Column(db.Integer, primary_key=True)
    xp_per_coin = db.Column(db.Integer, default=3)
    level_2_xp = db.Column(db.Integer, default=200)
    level_3_xp = db.Column(db.Integer, default=250)
    level_2_min_price = db.Column(db.Integer, default=100)
    level_3_min_price = db.Column(db.Integer, default=250)
    store_open_days = db.Column(db.String(32), default='2,5')  # 0=Mon ... 6=Sun

    def __repr__(self):
        return '<EconomySetting>'
