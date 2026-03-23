from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from config import Config
from sqlalchemy import inspect, text
import os

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
csrf = CSRFProtect()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Iltimos, tizimga kiring.'
    login_manager.login_message_category = 'info'

    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.student import student_bp
    from app.routes.store import store_bp
    from app.routes.admin import admin_bp
    from app.routes.transactions import transactions_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(store_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(transactions_bp)

    # Create tables and seed data
    with app.app_context():
        db.create_all()
        _ensure_user_economy_columns()
        _seed_economy_settings()
        _seed_initial_data()

    return app


def _seed_initial_data():
    from app.models import User, Wallet, Category, Product, Achievement
    from werkzeug.security import generate_password_hash

    admin_username_env = os.environ.get('ADMIN_USERNAME')
    admin_email = os.environ.get('ADMIN_EMAIL')
    admin_password = os.environ.get('ADMIN_PASSWORD')
    admin_username = admin_username_env or 'admin'

    # Create or update admin
    admin_user = User.query.filter_by(role='admin').first()
    if not admin_user:
        if admin_email and admin_password:
            admin = User(
                first_name='Administrator',
                last_name='Tizim',
                username=admin_username,
                email=admin_email,
                password_hash=generate_password_hash(admin_password),
                role='admin',
                is_active=True
            )
            db.session.add(admin)
            db.session.flush()
            wallet = Wallet(user_id=admin.id, balance=0)
            db.session.add(wallet)
        else:
            print("Admin user not created. Set ADMIN_EMAIL and ADMIN_PASSWORD environment variables.")
    else:
        # Keep admin account aligned with required credentials
        if admin_username_env:
            admin_user.username = admin_username_env
        if admin_email:
            admin_user.email = admin_email
        if admin_password:
            admin_user.password_hash = generate_password_hash(admin_password)
        if admin_user.first_name in (None, 'Administrator'):
            admin_user.first_name = 'Administrator'
        if admin_user.last_name in (None, 'Tizim'):
            admin_user.last_name = 'Tizim'
        if not admin_user.wallet:
            db.session.add(Wallet(user_id=admin_user.id, balance=0))

    # Seed categories
    if Category.query.count() == 0:
        cats = [
            Category(name="Jismoniy sovg'alar", description="Haqiqiy sovg'alar va mukofotlar"),
            Category(name='Raqamli bonuslar', description="Onlayn bonuslar va imtiyozlar"),
            Category(name='Sertifikatlar', description="Sertifikatlar va diplomlar"),
            Category(name='Imtiyozlar', description="Maxsus huquqlar va kirishlar"),
        ]
        for c in cats:
            db.session.add(c)
        db.session.flush()

        # Seed products
        cat1 = Category.query.filter_by(name="Jismoniy sovg'alar").first()
        cat2 = Category.query.filter_by(name='Raqamli bonuslar').first()
        products = [
            Product(title='Logotipli bloknot', description="Maktabning brendli bloknoti", price_coin=150, stock=20, category_id=cat1.id if cat1 else 1, is_active=True),
            Product(title='Ruchka-brelok', description="Brelokli zamonaviy ruchka", price_coin=80, stock=50, category_id=cat1.id if cat1 else 1, is_active=True),
            Product(title="Qo'shimcha vaqt", description="Test uchun 15 daqiqa qo'shimcha vaqt", price_coin=200, stock=999, category_id=cat2.id if cat2 else 2, is_active=True),
            Product(title="Bitta uy vazifasini o'tkazib yuborish", description="Bitta uy vazifasini topshirmaslik imkoniyati", price_coin=300, stock=999, category_id=cat2.id if cat2 else 2, is_active=True),
            Product(title='Krujka', description="Maktabning brendli krujkasi", price_coin=500, stock=10, category_id=cat1.id if cat1 else 1, is_active=True),
        ]
        for p in products:
            db.session.add(p)

    # Seed achievements
    if Achievement.query.count() == 0:
        achievements = [
            Achievement(title='Birinchi Coin!', description='Birinchi Coinni oling', icon='🎉', condition_type='total_earned', condition_value=1, is_active=True),
            Achievement(title="Jamg'arma 100", description='100 Coin jamlang', icon='💰', condition_type='total_earned', condition_value=100, is_active=True),
            Achievement(title="Jamg'arma 500", description='500 Coin jamlang', icon='🏆', condition_type='total_earned', condition_value=500, is_active=True),
            Achievement(title='Birinchi xarid', description="Do'konda birinchi xaridingizni qiling", icon='🛍️', condition_type='purchases', condition_value=1, is_active=True),
            Achievement(title='Xaridchi', description='5 ta xarid qiling', icon='🛒', condition_type='purchases', condition_value=5, is_active=True),
            Achievement(title='Hafta Top-1', description="Reytingda 1-o'rinni egallang", icon='⭐', condition_type='leaderboard_top1', condition_value=1, is_active=True),
        ]
        for a in achievements:
            db.session.add(a)

    # Update default seed data to Uzbek (for existing DBs)

    category_updates = {
        'Физические подарки': ("Jismoniy sovg'alar", "Haqiqiy sovg'alar va mukofotlar"),
        'Цифровые бонусы': ('Raqamli bonuslar', "Onlayn bonuslar va imtiyozlar"),
        'Сертификаты': ('Sertifikatlar', "Sertifikatlar va diplomlar"),
        'Привилегии': ('Imtiyozlar', "Maxsus huquqlar va kirishlar"),
    }
    for old_name, (new_name, new_desc) in category_updates.items():
        cat = Category.query.filter_by(name=old_name).first()
        if cat:
            cat.name = new_name
            cat.description = new_desc

    product_updates = {
        'Блокнот с логотипом': ('Logotipli bloknot', "Maktabning brendli bloknoti"),
        'Ручка-брелок': ('Ruchka-brelok', "Brelokli zamonaviy ruchka"),
        'Дополнительное время': ("Qo'shimcha vaqt", "Test uchun 15 daqiqa qo'shimcha vaqt"),
        'Пропуск одного ДЗ': ("Bitta uy vazifasini o'tkazib yuborish", "Bitta uy vazifasini topshirmaslik imkoniyati"),
        'Кружка': ('Krujka', "Maktabning brendli krujkasi"),
    }
    for old_title, (new_title, new_desc) in product_updates.items():
        product = Product.query.filter_by(title=old_title).first()
        if product:
            product.title = new_title
            product.description = new_desc

    achievement_updates = {
        'Первый Coin!': ('Birinchi Coin!', 'Birinchi Coinni oling'),
        'Копилка 100': ("Jamg'arma 100", '100 Coin jamlang'),
        'Копилка 500': ("Jamg'arma 500", '500 Coin jamlang'),
        'Первая покупка': ('Birinchi xarid', "Do'konda birinchi xaridingizni qiling"),
        'Шопоголик': ('Xaridchi', '5 ta xarid qiling'),
        'Топ недели': ('Hafta Top-1', "Reytingda 1-o'rinni egallang"),
    }
    for old_title, (new_title, new_desc) in achievement_updates.items():
        ach = Achievement.query.filter_by(title=old_title).first()
        if ach:
            ach.title = new_title
            ach.description = new_desc

    db.session.commit()


def _seed_economy_settings():
    from flask import current_app
    from app.models import EconomySetting

    if EconomySetting.query.first():
        return

    config = current_app.config
    open_days = config.get('STORE_OPEN_DAYS', (2, 5))
    setting = EconomySetting(
        xp_per_coin=config.get('XP_PER_COIN', 3),
        level_2_xp=config.get('LEVEL_2_XP', 200),
        level_3_xp=config.get('LEVEL_3_XP', 250),
        level_2_min_price=config.get('LEVEL_2_MIN_PRICE', 100),
        level_3_min_price=config.get('LEVEL_3_MIN_PRICE', 250),
        store_open_days=','.join(str(d) for d in open_days)
    )
    db.session.add(setting)
    db.session.commit()


def _ensure_user_economy_columns():
    from app.models import User

    inspector = inspect(db.engine)
    columns = {col['name'] for col in inspector.get_columns('users')}
    if 'xp' not in columns:
        db.session.execute(text('ALTER TABLE users ADD COLUMN xp INTEGER DEFAULT 0'))
    if 'level' not in columns:
        db.session.execute(text('ALTER TABLE users ADD COLUMN level INTEGER DEFAULT 1'))
    db.session.commit()

    User.query.filter(User.xp.is_(None)).update({'xp': 0})
    User.query.filter(User.level.is_(None)).update({'level': 1})
    db.session.commit()
