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
    MIIEogIBAAKCAQEAnzyis1ZjfNB0bBgKFMSvvkTtwlvBsaJq7S5wA+kzeVOVpVWw
    kWdVha4s38XM/pa/yr47av7+z3VTmvDRyAHcaT92whREFpLv9cj5lTeJSibyr/Mr
    m/YtjCZVWgaOYIhwrXwKLqPr/11inWsAkfIytvHWTxZYEcXLgAXFuUuaS3uF9gEi
    NQwzGTU1v0FqkqTBr4B8nW3HCN47XUu0t8Y0e+lf4s4OxQawWD79J9/5d3Ry0vbV
    3Am1FtGJiJvOwRsIfVChDpYStTcHTCMqtvWbV6L11BWkpzGXSW4Hv43qa+GSYOD2
    QU68Mb59oSk2OB+BtOLpJofmbGEGgvmwyCI9MwIDAQABAoIBACiARq2wkltjtcjs
    kFvZ7w1JAORHbEufEO1Eu27zOIlqbgyAcAl7q+/1bip4Z/x1IVES84/yTaM8p0go
    amMhvgry/mS8vNi1BN2SAZEnb/7xSxbflb70bX9RHLJqKnp5GZe2jexw+wyXlwaM
    +bclUCrh9e1ltH7IvUrRrQnFJfh+is1fRon9Co9Li0GwoN0x0byrrngU8Ak3Y6D9
    D8GjQA4Elm94ST3izJv8iCOLSDBmzsPsXfcCUZfmTfZ5DbUDMbMxRnSo3nQeoKGC
    0Lj9FkWcfmLcpGlSXTO+Ww1L7EGq+PT3NtRae1FZPwjddQ1/4V905kyQFLamAA5Y
    lSpE2wkCgYEAy1OPLQcZt4NQnQzPz2SBJqQN2P5u3vXl+zNVKP8w4eBv0vWuJJF+
    hkGNnSxXQrTkvDOIUddSKOzHHgSg4nY6K02ecyT0PPm/UZvtRpWrnBjcEVtHEJNp
    bU9pLD5iZ0J9sbzPU/LxPmuAP2Bs8JmTn6aFRspFrP7W0s1Nmk2jsm0CgYEAyH0X
    +jpoqxj4efZfkUrg5GbSEhf+dZglf0tTOA5bVg8IYwtmNk/pniLG/zI7c+GlTc9B
    BwfMr59EzBq/eFMI7+LgXaVUsM/sS4Ry+yeK6SJx/otIMWtDfqxsLD8CPMCRvecC
    2Pip4uSgrl0MOebl9XKp57GoaUWRWRHqwV4Y6h8CgYAZhI4mh4qZtnhKjY4TKDjx
    QYufXSdLAi9v3FxmvchDwOgn4L+PRVdMwDNms2bsL0m5uPn104EzM6w1vzz1zwKz
    5pTpPI0OjgWN13Tq8+PKvm/4Ga2MjgOgPWQkslulO/oMcXbPwWC3hcRdr9tcQtn9
    Imf9n2spL/6EDFId+Hp/7QKBgAqlWdiXsWckdE1Fn91/NGHsc8syKvjjk1onDcw0
    NvVi5vcba9oGdElJX3e9mxqUKMrw7msJJv1MX8LWyMQC5L6YNYHDfbPF1q5L4i8j
    8mRex97UVokJQRRA452V2vCO6S5ETgpnad36de3MUxHgCOX3qL382Qx9/THVmbma
    3YfRAoGAUxL/Eu5yvMK8SAt/dJK6FedngcM3JEFNplmtLYVLWhkIlNRGDwkg3I5K
    y18Ae9n7dHVueyslrb6weq7dTkYDi3iOYRW8HRkIQh06wEdbxt0shTzAJvvCQfrB
    jg/3747WSsf/zBTcHihTRBdAv6OmdhV4/dD5YBfLAkLrd+mX7iE=
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
