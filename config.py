import os
import secrets

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        # Dev fallback; set SECRET_KEY in production
        SECRET_KEY = secrets.token_urlsafe(32)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(BASE_DIR, 'coin_system.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'app', 'static', 'uploads')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    ITEMS_PER_PAGE = 20
    PASSWORD_RESET_TOKEN_EXPIRES = 3600  # seconds
    XP_PER_COIN = 3
    LEVEL_2_XP = 200
    LEVEL_3_XP = 250
    LEVEL_2_MIN_PRICE = 100
    LEVEL_3_MIN_PRICE = 250
    STORE_OPEN_DAYS = (2, 5)  # Wednesday (2) and Saturday (5)


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
