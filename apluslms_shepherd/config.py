from builtins import object, frozenset
import string
from os.path import dirname


class Config(object):
    DEBUG = False
    TESTING = False
    BASE_DIR = dirname(__file__)
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + BASE_DIR + '/shepherd.db'
    LOGIN_REDIRECT_URL = "/auth/success/"
    LOGIN_DISABLED = False
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
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    LTI_CONFIG = {
        'secret': {
            "Bleks2FiObiMpd5C": "uf7OtOjcCclxGZBzzRoll87vledSK8cK3koL6BRCSwelICYIc8eyG56qxDJKtV6l"
        }
    }
    USE_SSH_FOR_GIT = True
    CELERY_RESULT_BACKEND = "db+sqlite:///"+BASE_DIR+"/result.db"
    CELERY_BROKER_URL = "amqp://guest:guest@172.17.0.2:5672"
    CELERY_NAME = "test"
    CELERY_IMPORTS = ("apluslms_shepherd.celery_tasks.tasks",
                      "apluslms_shepherd.celery_tasks.signals"
                      )
    COURSE_REPO_BASEPATH = BASE_DIR+"/../../shepherd_test_clone/"
    BUILD_WEBHOOK_URL=""



class ProductionConfig(Config):
    DATABASE_URI = 'mysql://user@localhost/shepherd'


class DevelopmentConfig(Config):
    DEBUG = True
    BUILD_WEBHOOK_URL_TOKEN=""
    COURSE_DEPLOYMENT_PATH = Config.BASE_DIR+"/../../shepherd_deploy/"


class TestingConfig(Config):
    TESTING = True
