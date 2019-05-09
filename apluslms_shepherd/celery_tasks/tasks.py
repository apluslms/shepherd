import os
from os.path import dirname
import subprocess
try:
    from subprocess import DEVNULL # Python 3
except ImportError:
    DEVNULL = open(os.devnull, 'r+b', 0)
from datetime import datetime

from celery.result import AsyncResult
from celery.signals import before_task_publish
from celery.utils.log import get_task_logger
from celery.worker.control import revoke
from sqlalchemy import desc

from apluslms_shepherd.build.models import Build, BuildLog, States, Action
from apluslms_shepherd.courses.models import CourseInstance
from apluslms_shepherd.extensions import celery, db
from apluslms_shepherd.config import DevelopmentConfig

logger = get_task_logger(__name__)


@celery.task
def pull_repo(base_path, url, branch, course_key, instance_key, build_number):
    logger.info('url:{}, branch:{} course_key:{} instance_key{}'.format(url, branch, course_key, instance_key))
    folder = url.split('/')[-1]
    logger.info(folder)
    logger.info("Pulling from {}".format(url))
    shell_script_path = os.path.join(DevelopmentConfig.BASE_DIR, 'celery_tasks/shell_script/pull_bare.sh')
    cmd = [shell_script_path, base_path, folder, url, branch,
           course_key, instance_key, build_number]
    print(cmd)
    proc = subprocess.Popen(cmd, stdin=DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            env=dict(os.environ, SSH_ASKPASS="echo", GIT_TERMINAL_PROMPT="0"))
    o, e = proc.communicate()
    logger.info('Output: ' + o.decode('ascii'))
    logger.info('code: ' + str(proc.returncode))
    return str(proc.returncode) + '|' + o.decode('ascii')


@celery.task
def build_repo(pull_result, base_path, course_key, instance_key, build_number):
    # build the material
    logger.info("pull_repo result:" + pull_result)
    # Check the result of last step
    if pull_result.split('|')[0] is not '0':
        logger.error('The clone task was failed, aborting the build task')
        return '-1|The clone task was failed, aborting the build task'
    logger.info(
        "The repo has been pulled, Building the course, course key:{}, branch:{}".format(course_key, instance_key))
    shell_script_path = os.path.join(DevelopmentConfig.BASE_DIR, 'celery_tasks/shell_script/build_roman.sh')
    cmd = [shell_script_path, base_path, course_key, instance_key, build_number]
    proc = subprocess.Popen(cmd, stdin=DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    o, e = proc.communicate()
    logger.info('Output: ' + o.decode('ascii'))
    logger.info('code: ' + str(proc.returncode))
    return str(proc.returncode) + '|' + o.decode('ascii')


@celery.task
def deploy(build_result, base_path, course_key, instance_key, build_id):
    pass


# For some reason this func is not working if in signal.py. Other signal handling functions works fine
@before_task_publish.connect(sender='apluslms_shepherd.celery_tasks.tasks.pull_repo')
def clone_task_before_publish(sender=None, headers=None, body=None, **kwargs):
    # information about task are located in headers for task messages
    # using the task protocol version 2.
    info = headers if 'task' in headers else body
    print('before_task_publish for task id {info[id]}'.format(
        info=info,
    ))
    # Get course key and instance_key from the header
    res = eval(headers['argsrepr'])
    course_key = res[-3]
    instance_key = res[-2]
    current_build_number = res[-1]
    print('course_key:{}, instance_key:{}'.format(course_key, instance_key))
    now = datetime.utcnow()
    ins = CourseInstance.query.filter_by(course_key=course_key, key=instance_key).first()
    if ins is None:
        print('No such course instance inthe database')
        revoke(info["id"], terminate=True)
        return
    # Create new build entry and buildlog entry
    build = Build(instance_id=ins.id, start_time=now,
                  state=States.PUBLISH,
                  action=Action.CLONE, number=current_build_number)
    new_log_entry = BuildLog(
        instance_id=ins.id,
        start_time=now,
        number=current_build_number,
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
