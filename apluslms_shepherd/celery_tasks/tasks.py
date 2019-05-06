import subprocess
from datetime import datetime

from celery.result import AsyncResult
from celery.signals import before_task_publish
from celery.utils.log import get_task_logger
from celery.worker import request

from apluslms_shepherd.build.models import Build, BuildLog, States, Action
from apluslms_shepherd.courses.models import CourseInstance
from apluslms_shepherd.extensions import celery, db

logger = get_task_logger(__name__)


@celery.task(bind=True, default_retry_delay=10)
def pull_repo(self, base_path, url, branch, course_key, instance_key):
    logger.info('url:{}, branch:{} course_key:{} instance_key{}'.format(url, branch, course_key, instance_key))
    ins = CourseInstance.query.filter_by(git_origin=url, branch=branch).first()
    folder = url.split('/')[-1]
    logger.info(folder)
    logger.info("Pulling from {}".format(url))
    cmd = ["bash", "apluslms_shepherd/celery_tasks/shell_script/pull_bare.sh", base_path, folder, url, branch,
           course_key]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    o, e = proc.communicate()
    logger.info('Output: ' + o.decode('ascii'))
    logger.info('code: ' + str(proc.returncode))
    # Store current task id in db
    return o.decode('ascii')


@celery.task(bind=True, default_retry_delay=10)
def build_repo(self, pull_result, base_path, course_key, branch):
    # build the material
    print("pull_repo result:" + pull_result)
    print("The repo has been pulled, Building the course, course key:{}, branch:{}".format(course_key, branch))

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
    # Change build status
    now = datetime.utcnow()
    build = Build.query.filter_by(course_key=course_key, instance_key=instance_key).first()
    if build is None:
        build = Build(course_key=course_key, instance_key=instance_key, start_time=now, status=States.PUBLISH,
                      action=Action.PUBLISH if sender.__name__ is 'pull_repo' else Action.BUILD.CLONE)
        db.session.add(build)
    else:
        build.status = States.RUNNING
    print('build')
    new_log_entry = BuildLog(
        task_id=info["id"] + '-PUBLISH',
        course_key=course_key,
        instance_key=instance_key,
        start_time=now,
        status=States.PUBLISH,
        action=Action.CLONE
    )
    print('clone_log')
    db.session.add(new_log_entry)
    db.session.commit()


@celery.task
def error_handler(uuid):
    result = AsyncResult(uuid)
    exc = result.get(propagate=False)
    print('Task {0} raised exception: {1!r}\n{2!r}'.format(
        uuid, exc, result.traceback))