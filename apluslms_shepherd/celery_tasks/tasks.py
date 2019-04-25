# from apluslms_shepherd.auth.models import db
from apluslms_shepherd.celery_tasks import app as celery_app
# from apluslms_shepherd.courses.models import CourseInstance
from celery.utils.log import get_task_logger


import subprocess

logger = get_task_logger(__name__)


@celery_app.task(bind=True, default_retry_delay=10)
def pull_repo(self, path, url, branch):
    logger.info("Pulling from {}".format(url))
    cmd = ["bash", "/u/18/dingr1/unix/code/shepherd/apluslms_shepherd/celery_tasks/shell_script/pull.sh", path, url, branch]
    proc = subprocess.Popen(cmd)
    logger.info(self.request.id)
    o, e = proc.communicate()

    # logger.info('Output: ' + o.decode('ascii'))
    # logger.info('Error: ' + e.decode('ascii'))
    # logger.info('code: ' + str(proc.returncode))
    # Store current task id in db
    # ins = CourseInstance.query.filter_by(git_origin=url, branch=branch).first()
    # ins.pull_task_id = self.request.id
    # db.session.commit()
    return o.decode('ascii')


@celery_app.task(bind=True, default_retry_delay=10)
def build_repo(self):
    pass
