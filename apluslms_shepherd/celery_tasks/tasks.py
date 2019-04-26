import os

from apluslms_shepherd.auth.models import db
from apluslms_shepherd.extensions import celery
from apluslms_shepherd.courses.models import CourseInstance
from celery.utils.log import get_task_logger


import subprocess

logger = get_task_logger(__name__)


@celery.task(bind=True, default_retry_delay=10)
def pull_repo(self, base_path, url, branch):
    logger.info('url:{}, branch:{}'.format(url, branch))
    ins = CourseInstance.query.filter_by(git_origin=url, branch=branch).first()
    folder = url.split('/')[-1]
    logger.info(folder)
    logger.info("Pulling from {}".format(url))
    cmd = ["bash", "apluslms_shepherd/celery_tasks/shell_script/pull_bare.sh", base_path, folder, url, branch, ins.course_key]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    o, e = proc.communicate()
    logger.info('Output: ' + o.decode('ascii'))
    logger.info('code: ' + str(proc.returncode))
    # Store current task id in db

    ins.pull_task_id = self.request.id
    db.session.commit()
    return o.decode('ascii')


@celery.task(bind=True, default_retry_delay=10)
def build_repo(self):
    pass
