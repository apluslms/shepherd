class CelerySettingDev(object):
    CELERY_BACKEND = "db+sqlite:////u/18/dingr1/unix/code/shepherd/result.db"
    CELERY_BROKER_ADDRESS = "amqp://guest:guest@172.17.0.2:5672"
    CELERY_NAME = "test"