import os
import secrets

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def _build_database_uri():
    db_url = os.environ.get('DATABASE_URL') or os.environ.get('POSTGRES_URL')
    if db_url and db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)
    return db_url or ('sqlite:///' + os.path.join(BASE_DIR, 'coin_system.db'))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        # Dev fallback; set SECRET_KEY in production
        SECRET_KEY = secrets.token_urlsafe(32)
    SQLALCHEMY_DATABASE_URI = _build_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
    }
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or os.path.join(BASE_DIR, 'app', 'static', 'uploads')
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
    INIT_DB_ON_STARTUP = True
    ENABLE_LOCAL_UPLOADS = True


class ProductionConfig(Config):
    DEBUG = False
    INIT_DB_ON_STARTUP = False
    ENABLE_LOCAL_UPLOADS = False
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PREFERRED_URL_SCHEME = 'https'


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
