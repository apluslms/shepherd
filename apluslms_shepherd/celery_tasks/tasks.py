import subprocess
from datetime import datetime

from celery.result import AsyncResult
from celery.signals import before_task_publish
from celery.utils.log import get_task_logger
from celery.worker.control import revoke
from sqlalchemy import desc

from apluslms_shepherd.build.models import Build, BuildLog, States, Action
from apluslms_shepherd.courses.models import CourseInstance
from apluslms_shepherd.extensions import celery, db

logger = get_task_logger(__name__)


@celery.task(bind=True, default_retry_delay=10)
def pull_repo(self, base_path, url, branch, course_key, instance_key):
    logger.info('url:{}, branch:{} course_key:{} instance_key{}'.format(url, branch, course_key, instance_key))
    folder = url.split('/')[-1]
    logger.info(folder)
    logger.info("Pulling from {}".format(url))
    cmd = ["bash", "apluslms_shepherd/celery_tasks/shell_script/pull_bare.sh", base_path, folder, url, branch,
           course_key]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    o, e = proc.communicate()
    logger.info('Output: ' + o.decode('ascii'))
    logger.info('code: ' + str(proc.returncode))
    return str(proc.returncode) + '|' + o.decode('ascii')


@celery.task(bind=True, default_retry_delay=10)
def build_repo(self, pull_result, base_path, course_key, instance_key):
    # build the material
    logger.info("pull_repo result:" + pull_result)
    logger.info(
        "The repo has been pulled, Building the course, course key:{}, branch:{}".format(course_key, instance_key))
    cmd = ["bash", "apluslms_shepherd/celery_tasks/shell_script/build_roman.sh", base_path, course_key, instance_key]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    o, e = proc.communicate()
    logger.info('Output: ' + o.decode('ascii'))
    logger.info('code: ' + str(proc.returncode))
    return str(proc.returncode) + '|' + o.decode('ascii')


# For some reason this func is not working if in signal.py. Other signal handling functions works fine
@before_task_publish.connect(sender='apluslms_shepherd.celery_tasks.tasks.pull_repo')
def clone_task_before_publish(sender=None, headers=None, body=None, **kwargs):
    # information about task are located in headers for task messages
    # using the task protocol version 2.
    info = headers if 'task' in headers else body
    print('before_task_publish for task id {info[id]}'.format(
        info=info,
    ))
    res = eval(headers['argsrepr'])
    course_key = res[-2]
    instance_key = res[-1]
    print('course_key:{}, instance_key:{}'.format(course_key, instance_key))
    now = datetime.utcnow()
    ins = CourseInstance.query.filter_by(course_key=course_key, key=instance_key).first()
    if ins is None:
        print('No such course instance inthe database')
        revoke(info["id"], terminate=True)
        return
    # current_build_number = 0 if Build.query.filter_by(instance_id=ins.id) is None \
    #     else Build.query.filter_by(instance_key=ins.id).order_by(desc(Build.number)).first().number
    current_build_number = 0 if Build.query.filter_by(instance_id=ins.id) is None \
        else Build.query.filter_by(instance_id=ins.id).order_by(
        desc(Build.number)).first().number
    print(current_build_number)
    # Create new build entry and buildlog entry
    build = Build(instance_id=ins.id, course_key=course_key, instance_key=instance_key, start_time=now,
                  state=States.PUBLISH,
                  action=Action.CLONE, number=current_build_number + 1)
    new_log_entry = BuildLog(
        instance_id=ins.id,
        course_key=course_key,
        instance_key=instance_key,
        start_time=now,
        number=current_build_number + 1,
        action=Action.CLONE
    )
    print('clone_log')
    db.session.add(new_log_entry)
    db.session.add(build)
    db.session.commit()
    print('Task sent')


@celery.task
def error_handler(uuid):
    result = AsyncResult(uuid)
    exc = result.get(propagate=False)
    print('Task {0} raised exception: {1!r}\n{2!r}'.format(
        uuid, exc, result.traceback))
