from __future__ import absolute_import
from celery import Celery
from .config import CelerySettingDev

app = Celery(
    CelerySettingDev.CELERY_NAME,
    broker=CelerySettingDev.CELERY_BROKER_ADDRESS,
    backend=CelerySettingDev.CELERY_BROKER_ADDRESS,
    include=['apluslms_shepherd.celery_tasks.tasks'])
