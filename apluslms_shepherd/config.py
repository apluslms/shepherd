import string
from builtins import object, frozenset
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
    CELERY_RESULT_BACKEND = "db+sqlite:///" + BASE_DIR + "/result.db"
    BROKER_URL = "amqp://guest:guest@172.17.0.2:5672"
    CELERY_NAME = "test"
    CELERY_IMPORTS = ("apluslms_shepherd.celery_tasks.build",
                      "apluslms_shepherd.celery_tasks.repos"
                      )
    COURSE_REPO_BASEPATH = BASE_DIR + "/../../shepherd_test_clone/"
    JWT_PRIVATE_KEY = """
    -----BEGIN RSA PRIVATE KEY-----
    MIIEowIBAAKCAQEA0QIB6wP5rGpT7pcKM0uQbn3FbQI2Xp58vLW+eLISgPvh0EMN
    uVWMazRfTBGnSxYI2P2F+Yf+O8Ck3JWOpuCD+i0a+RlC7gZdspULHpRYSccOqvRd
    cMn93nuPxiHJ+zAFuVR6mmDQmkHR3ruFvbQtFWABpbZpqVOlaOUqoyQcp7JGOrrG
    ZZhifS8EE56azvhIm8n2qf+KhKkTq0P71j+43h2sZtHM9nrsm/wtyb26xPBwGS1v
    1d5bWw0D2vhPSCP4HV2DuI6WD6pEN9Axjf5jdG7tGa6GnyPchdDAvlnA1FQiFfkz
    4NQtL5upmGiz6gBslFlPhZmejlr2RUYd4mbQ3QIDAQABAoIBADynk3zrg2p41PC5
    nnkyZbDbCQ9QhAzDe7mcGLGYI+yQrICu5O2zGPQHl9xQhzcwJtMqB9ZZk/stNerZ
    8DMXltVkf55oqVbAPDLWNArkzBZlESmljvRreiQ1wYyjQ6WE0zRsgsQIcqFBlrFH
    xFFAV5ELco7vuAwuvSMK1mvP0A0OFiaTRv0rOZknB4mzeQ3wHoLWDMb3kQtX8lr4
    0/SjuczyeR2NxheO0peMRmY5E3LZjVV8JTqZ0DuuA37VxS3DlijKM9dwaCVDJc6I
    grWK7xhKAg15xge0t6HtMfiFXQDQRHLqC0Sk9s7VDja4SyVMhReY6IOEaLFn9HtV
    7AJ7uNUCgYEA7rCEx/M46XFPBt5+Jgl56VrFNbZe1I6cDlN5bYgwkq6Ey76LfopC
    D2hMAhc9nyUOfloCWxT6hzf7ctG4dZv4faSpfrfxmB2a3ArbC5sEjw+8F13REpPK
    NQ7Ry5li1BdOqE9PG2smcS1kozHHC+MSpK9t1tuCaE4tRr5UuORXnDMCgYEA4Cps
    FT4M1/nsjTja6RNit/9yPo/vzYtuu5GL7SqRoGwxARG1xnTg0Zgd30pTSi84c2G1
    HpioIoJdGlv/0d8zYW4vluArt2DHsJ9yLU+ngwX20WEzBs7j6bv7XXcG7AJWgLEw
    UYWSccc77IUZPSGm4W07QxZFgyNTEPLEcjfmzq8CgYBgyaVeKytlxfOktm3y4J7V
    2F/lsujrSlTPnlu75aDEqg3hTIfmLQwykTlZE7GCKhWheMBBzNT2JeZJne8tiayO
    zkmIv/AwnbihB6nhH+AOXvQHiZxw6wrwzuyVocIofLcBmv9Z/+4bsKuBXXr4QADc
    VOK2YFaWEzVa3W0feEBqbwKBgFnvCx/WniaEIXBjEAiUe3WgaYBKFQZc21crRH0p
    J/W5kkuAhHITcCMGqW1tD09i9H3uBFE7I7F8pceug0r7Bk0ffL5GP6O5k0P8JD2j
    iGwbl3NXULZ5iJy8i1NrLn6/TV8iN2Vtdlxpd1Qj7gVFnAMy5KS8qbS8FlZlX4UH
    gnUHAoGBAOYMDhl1LpMGNOY0MFbDfbewImNFRANGID6/ZZIqBsDHh+7mwWpGcgd8
    Ue5mZPtGKR1RRDdxFoeOzxZTxevSyMP1kd2AWoORD3sF/5jP4U8LOdDzGQZdpTOO
    XjA/sG6+VSb9Mw6FLel7sUPGEqnCOKHjr7aO19RWLt1LdVyBxRW9
    -----END RSA PRIVATE KEY-----
    """
    JWT_ALGORITHM = "RS256"
    JWT_ISSUER = "shepherd"


class ProductionConfig(Config):
    DATABASE_URI = 'mysql://user@localhost/shepherd'


class DevelopmentConfig(Config):
    DEBUG = True
    BUILD_WEBHOOK_TOKEN = "Secret"
    BUILD_WEBHOOK_URL = "http://127.0.0.1:5000/webhooks/state/"
    COURSE_DEPLOYMENT_PATH = Config.BASE_DIR + "/../../shepherd_deploy/"


class TestingConfig(Config):
    TESTING = True
