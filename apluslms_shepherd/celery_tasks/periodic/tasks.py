from apluslms_shepherd.celery_tasks.repos.tasks import validate_deploy_key_scheduled
from apluslms_shepherd.config import DevelopmentConfig
from apluslms_shepherd.extensions import celery


@celery.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(
        10.0,
        validate_deploy_key_scheduled.s(DevelopmentConfig.REPO_KEYS_PATH)
    )
