from apluslms_shepherd.config import DevelopmentConfig
from apluslms_shepherd.extensions import celery
from apluslms_shepherd.repos.tasks.tasks import validate_deploy_key_scheduled

celery.conf.broker_url = "amqp://guest:guest@172.17.0.2:5672"


@celery.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(
        10.0,
        validate_deploy_key_scheduled.s(DevelopmentConfig.REPO_KEYS_PATH)
    )
