import os
import shutil
import subprocess

from apluslms_shepherd.celery_tasks.build.signals import task_action_mapping
from apluslms_shepherd.celery_tasks.build.utils import bare_clone
from apluslms_shepherd.celery_tasks.repos.utils import slugify

try:
    from subprocess import DEVNULL  # Python 3
except ImportError:
    DEVNULL = open(os.devnull, 'r+b', 0)

from celery.result import AsyncResult
from celery.utils.log import get_task_logger

from apluslms_shepherd.build.models import BuildState
from apluslms_shepherd.courses.models import CourseInstance
from apluslms_shepherd.extensions import celery
from apluslms_shepherd.config import DevelopmentConfig

from .helper import get_current_build_number_list, update_frontend

logger = get_task_logger(__name__)


@celery.task
def update_state(instance_id, build_number, state, action, log):
    """
    Take the updated state to MQ, this task is not going to the worker
    """
    logger.info("Sending state to frontend")


@celery.task
def pull_repo(base_path, url, branch, course_key, instance_key, build_number):
    """
    Clone bear repo to local, or update local one, generate working tree.
    """
    logger.info('url:{}, branch:{} course_key:{} instance_key{}'.format(url, branch, course_key, instance_key))
    logger.info("Pulling from {}".format(url))
    args = [base_path, url, course_key, instance_key, branch, build_number,
            os.path.join(DevelopmentConfig.REPO_KEYS_PATH, slugify(url), 'private.pem')]
    return_code = bare_clone(*args)
    return str(return_code) + "|"


@celery.task
def build_repo(pull_result, base_path, course_key, instance_key, build_number):
    """
    build the course material with roman
    """
    logger.info("pull_repo result:" + pull_result)
    # Check the result of last step
    if pull_result.split('|')[0] is not '0':
        logger.error('The clone task was failed, aborting the build task')
        return '-1|The clone task was failed, aborting the build task'
    log = "The repo has been pulled, Building the course, course key:{}, branch:{}".format(course_key, instance_key)
    logger.info(log)
    ins = CourseInstance.query.filter_by(course_key=course_key, instance_key=instance_key).first()
    update_frontend(ins.id, build_number, task_action_mapping['build_repo'], BuildState.RUNNING,
                    log)
    number_list = get_current_build_number_list()
    log = "Current build task number of this instance in the queue:{}".format(number_list)
    update_frontend(ins.id, build_number, task_action_mapping['build_repo'], BuildState.RUNNING,
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
    none_to_empty = lambda s: '' if s is None else str(s)
    cmd = [shell_script_path, base_path, course_key, instance_key, build_number, none_to_empty(ins.config_filename)]
    proc = subprocess.Popen(cmd, stdin=DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    o, e = proc.communicate()
    update_frontend(ins.id, build_number, task_action_mapping['build_repo'], BuildState.RUNNING,
                    o.decode('ascii'))
    logger.info('Output: ' + o.decode('ascii'))
    logger.info('code: ' + str(proc.returncode))
    return str(proc.returncode) + "|" + "Build Succeed" if proc.returncode == 0 else str(
        proc.returncode) + "|" + "Build Failed"


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
        logger.error('Error:' + why.strerror)
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


@celery.task
def error_handler(uuid):
    result = AsyncResult(uuid)
    exc = result.get(propagate=False)
    print('Task {0} raised exception: {1!r}\n{2!r}'.format(
        uuid, exc, result.traceback))
