import os
import shutil
import subprocess

from apluslms_shepherd.celery_tasks.signals import task_action_mapping

try:
    from subprocess import DEVNULL  # Python 3
except ImportError:
    DEVNULL = open(os.devnull, 'r+b', 0)
from datetime import datetime

from celery.result import AsyncResult
from celery.signals import before_task_publish
from celery.utils.log import get_task_logger
from celery.worker.control import revoke

from apluslms_shepherd.build.models import Build, BuildLog, State, Action
from apluslms_shepherd.courses.models import CourseInstance
from apluslms_shepherd.extensions import celery, db
from apluslms_shepherd.config import DevelopmentConfig

from .helper import get_current_build_number_list, WebHook, update_frontend

logger = get_task_logger(__name__)


@celery.task
def update_state(instance_id, build_number, state, action, log):
    print("Sending state to frontend")
    """
    Take the updated state to MQ, this task is not going to the worker
    """


@celery.task
def pull_repo(base_path, url, branch, course_key, instance_key, build_number):
    """
    Clone bear repo to local, or update local one, generate working tree.
    """
    logger.info('url:{}, branch:{} course_key:{} instance_key{}'.format(url, branch, course_key, instance_key))
    folder = url.split('/')[-1]
    logger.info("Pulling from {}".format(url))
    shell_script_path = os.path.join(DevelopmentConfig.BASE_DIR, 'celery_tasks/shell_script/pull_bare.sh')
    cmd = [shell_script_path, base_path, folder, url, branch,
           course_key, instance_key, build_number]
    proc = subprocess.Popen(cmd, stdin=DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            env=dict(os.environ, SSH_ASKPASS="echo", GIT_TERMINAL_PROMPT="0"))
    o, e = proc.communicate()
    logger.info('Output: ' + o.decode('ascii'))
    logger.info('code: ' + str(proc.returncode))

    return str(proc.returncode) + "|" + o.decode('ascii').rstrip('\n\r')


@celery.task
def build_repo(pull_result, base_path, course_key, instance_key, build_number):
    """
    build the material
    """
    logger.info("pull_repo result:" + pull_result)
    # Check the result of last step
    if pull_result.split('|')[0] is not '0':
        logger.error('The clone task was failed, aborting the build task')
        return '-1|The clone task was failed, aborting the build task'
    log = "The repo has been pulled, Building the course, course key:{}, branch:{}".format(course_key, instance_key)
    logger.info(log)
    ins = CourseInstance.query.filter_by(course_key=course_key, key=instance_key).first()
    update_frontend(ins.id, build_number, task_action_mapping['build_repo'], State.RUNNING,
                    log)
    number_list = get_current_build_number_list()
    log = "Current build task number of this instance in the queue:{}".format(number_list)
    update_frontend(ins.id, build_number, task_action_mapping['build_repo'], State.RUNNING,
                    log)
    try:
        if int(build_number) < max(number_list):
            print(
                "Already have newer version in the task queue, task with build number {} aborted.".format(build_number))
            print("Current build numbers:{}".format(number_list))
            return "-1|Already have newer version in the task queue, task with build number {} aborted.".format(
                build_number)
    except (ValueError, TypeError):
        logger.error("Cannot compare current  build number with max number in the queue")
    shell_script_path = os.path.join(DevelopmentConfig.BASE_DIR, 'celery_tasks/shell_script/build_roman.sh')
    cmd = [shell_script_path, base_path, course_key, instance_key, build_number]
    proc = subprocess.Popen(cmd, stdin=DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    o, e = proc.communicate()
    update_frontend(ins.id, build_number, task_action_mapping['build_repo'], State.RUNNING,
                    o.decode('ascii'))
    logger.info('Output: ' + o.decode('ascii'))
    logger.info('code: ' + str(proc.returncode))
    return str(proc.returncode) + "|" + "Build Succeed"


@celery.task
def deploy(build_result, deploy_base_path, base_path, course_key, instance_key, build_number):
    """
    Copy the build filed to deploy folder
    TODO: Support remote deploy location(Cloud .etc)
    """
    # Check the last step
    logger.info("build_repo result{}".format(build_result))
    if build_result.split('|')[0] is not '0':
        logger.error('The build task was failed, aborting the deployment task')
        return '-1|The clone task was failed or aborted, aborting the build task'
    # Check is there has a newer version in the queue.If true, cancel the task and start cleaning
    number_list = get_current_build_number_list()
    if int(build_number) < max(number_list):
        print("Already have newer version in the task queue, task with build number {} aborted.".format(build_number))
        print("Current build numbers:{}".format(number_list))
        return "-1|Newer version in the task queue, task with build number {} aborted. Cleaning the local repo" \
            .format(build_number)
    logger.info(
        "The repo has been build, deploying the course, course key:{}, branch:{}".format(course_key, instance_key))
    try:
        build_path = os.path.join(base_path, 'builds', course_key, instance_key, build_number, "_build")
        # deploy_files = os.listdir(build_path)
        deploy_path = os.path.join(deploy_base_path, course_key, instance_key, build_number)
        shutil.move(build_path, deploy_path)
    except (FileNotFoundError, OSError, IOError) as why:
        logger.info('Error:' + why.strerror)
        return '-1|Error when deploying files'
    return '0' + '|File successfully moved to deployment folder.'


@celery.task
def clean(res, base_path, course_key, instance_key, build_number):
    """
    Clean the generated working tree.
    """
    print('Cleaning repo')
    path = os.path.join(base_path, 'builds', course_key, instance_key, build_number)
    try:
        print("Local work tree of build number {} deleted".format(build_number))
        shutil.rmtree(path)
        return res + '. Repo cleaned.'
    except (FileNotFoundError, IOError, OSError) as why:
        logger.info('Error:' + why.strerror)
        return '-1|Error when cleaning local worktree files,'


# For some reason this func is not working if in signal.py. Other signal handling functions works fine
@before_task_publish.connect(sender='apluslms_shepherd.celery_tasks.tasks.pull_repo')
def clone_task_before_publish(sender=None, headers=None, body=None, **kwargs):
    """
    information about task are located in headers for task messages
    Only be triggered when publish the "pull_repo" task
    """
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
        print('No such course instance in the database')
        revoke(info["id"], terminate=True)
        return
    # Create new build entry and buildlog entry
    build = Build(instance_id=ins.id, start_time=now,
                  state=State.PUBLISH,
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
    update_frontend(ins.id, current_build_number, Action.CLONE, State.PUBLISH,
                    "Instance with course_key:{}, instance_key:{} entering task queue, this is build No.{}".format(
                        sender.__name__,
                        course_key,
                        instance_key,
                        current_build_number))
    print('Current state sent to frontend')


@celery.task
def error_handler(uuid):
    result = AsyncResult(uuid)
    exc = result.get(propagate=False)
    print('Task {0} raised exception: {1!r}\n{2!r}'.format(
        uuid, exc, result.traceback))
