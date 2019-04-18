from builtins import object, frozenset
import string

class Config(object):
    DEBUG = False
    TESTING = False
    DATABASE_URI = 'sqlite:///shepherd.db'
    LOGIN_REDIRECT_URL = "/auth/success"
    BASE_CHARACTERS = string.ascii_letters + string.digits
    SAFE_CHARACTERS = frozenset(BASE_CHARACTERS + '-')
    KEY_LENGTH_RANGE = (6, 128)
    NONCE_LENGTH = (6, 128)
    SECRET_LENGTH_RANGE = (6, 128)
    KEY_LENGTH = 16
    SECRET_LENGTH = 64
    USER_NAME_LENGTH = 120
    FIRST_NAME_LENGTH = 50
    LAST_NAME_LENGTH = 50
    EMAIL_LENGTH = 50
    CREATE_UNKNOWN_USER = True
    SECRET_KEY = 'my super secret key'.encode('utf8')
    SQLALCHEMY_DATABASE_URI = 'sqlite:///app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    LTI_CONFIG = {
        'secret': {
            "Bleks2FiObiMpd5C": "uf7OtOjcCclxGZBzzRoll87vledSK8cK3koL6BRCSwelICYIc8eyG56qxDJKtV6l"
        }
    }

class ProductionConfig(Config):
    DATABASE_URI = 'mysql://user@localhost/shepherd'

class DevelopmentConfig(Config):
    DEBUG = True

class TestingConfig(Config):
    TESTING = True
