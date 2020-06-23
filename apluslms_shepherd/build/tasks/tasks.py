import os
import shutil

from datetime import datetime

from apluslms_shepherd.build.tasks.utils import bare_clone, get_current_build_number_list, roman_build, slugify
from apluslms_shepherd.observer.observer import ShepherdObserver
from apluslms_shepherd.observer.utils import get_logger, BrokerClient

try:
    from subprocess import DEVNULL  # Python 3
except ImportError:
    DEVNULL = open(os.devnull, 'r+b', 0)

from celery.result import AsyncResult
from celery.utils.log import get_task_logger

from apluslms_shepherd.build.models import BuildState, BuildStep, Build
from apluslms_shepherd.extensions import celery, db
from apluslms_shepherd.config import DevelopmentConfig

logger = get_task_logger(__name__)


@celery.task
def update_state(course_id, build_number, state, step, roman_step, log):
    """
    Take the updated state to MQ, this task is not going to the worker
    """
    logger.info("Sending state to frontend")


@celery.task
def pull_repo(base_path, url, branch, course_id, course_key, instance_key, build_number):
    """
    Clone bear repo to local, or update local one, generate working tree.
    """
    build = Build(course_id=course_id, number=build_number, start_time=datetime.utcnow(), result=BuildState.NONE)
    db.session.add(build)
    db.session.commit()
    course_info = {'course_id': course_id, 'number': build_number}
    observer_logger = get_logger(db.session, course_info)
    observer = ShepherdObserver(observer_logger, BrokerClient('apluslms_shepherd.celery_tasks.build.tasks.update_state',
                                                              'celery_state', course_info))
    observer.enter_prepare()
    observer.shepherd_step_start(BuildStep.CLONE)
    observer.shepherd_msg(BuildStep.CLONE, BuildState.RUNNING,
                          'url:%s, branch:%s course_key:%s instance_key:%s' % (url, branch, course_key, instance_key))
    logger.info('url:%s, branch:%s course_key:%s instance_key:%s', url, branch, course_key, instance_key)
    observer.shepherd_msg(BuildStep.CLONE, BuildState.RUNNING,
                          "Pulling from %s" % url)
    logger.info("Pulling from %s", url)
    args = [base_path, url, course_key, instance_key, branch, build_number,
            os.path.join(DevelopmentConfig.REPO_KEYS_PATH, slugify(url), 'private.pem'), observer]
    return_code = bare_clone(*args)
    observer.shepherd_step_end(BuildStep.CLONE, BuildState.SUCCESS if return_code == 0 else BuildState.FAILED)
    return {'code': return_code, 'msg': ''}


@celery.task
def build_repo(pull_result, base_path, course_id, course_key, instance_key, build_number):
    """
    build the course material with roman
    """
    course_info = {'course_id': course_id, 'number': build_number}
    observer_logger = get_logger(db.session, course_info)
    observer = ShepherdObserver(observer_logger, BrokerClient('apluslms_shepherd.celery_tasks.build.tasks.update_state',
                                                              'celery_state', course_info))
    observer.enter_build()
    observer.shepherd_step_start(BuildStep.BUILD)
    logger.info("pull_repo result: %s", str(pull_result))
    observer.shepherd_msg(BuildStep.BUILD, BuildState.RUNNING, "pull_repo result: %s" % pull_result)
    # Check the result of last step
    if not pull_result['code'] == 0:
        logger.error('The clone task was failed, aborting the build task')
        observer.shepherd_msg(BuildStep.BUILD, BuildState.CANCELED,
                              'The clone task was failed, aborting the build task')
        observer.shepherd_step_end(BuildStep.BUILD, BuildState.CANCELED)
        return {'code': -1, 'msg': 'The clone task was failed, aborting the build task.'}
    log = "The repo has been pulled, Building the course, course key:{}, branch:{}".format(course_key, instance_key)
    logger.info(log)
    observer.shepherd_msg(BuildStep.BUILD, BuildState.RUNNING, log)
    number_list = get_current_build_number_list()
    log = "Current build task number of this instance in the queue:{}".format(number_list)
    observer.shepherd_msg(BuildStep.BUILD, BuildState.RUNNING, log)
    logger.info(log)
    try:
        if int(build_number) < max(number_list):
            logger.warning("Already have newer version in the task queue, task with build number %s aborted.",
                           build_number)
            observer.shepherd_msg(BuildStep.BUILD, BuildState.CANCELED,
                                  "Already have newer version in the task queue, task with build number %s aborted." % build_number)
            observer.shepherd_step_end(BuildStep.BUILD, BuildState.CANCELED)
            return {'code': 5, 'msg': "Already have newer version in the task queue, task with build number {} "
                                      "aborted.".format(build_number)}
    except (ValueError, TypeError):
        log = "Cannot compare current  build number with max number in the queue"
        logger.error(log)
        observer.shepherd_msg(BuildStep.BUILD, BuildState.FAILED,
                              log)
        observer.shepherd_step_end(BuildStep.BUILD, BuildState.FAILED)
        return {'code': 1, 'msg': log}
    return_code = roman_build(base_path, course_key, instance_key, build_number, observer)
    observer.shepherd_step_end(BuildStep.BUILD, BuildState.SUCCESS if return_code == 0 else BuildState.FAILED)
    return {'code': return_code, 'msg': 'Build success'}


@celery.task
def deploy(build_result, deploy_base_path, base_path, course_id, course_key, instance_key, build_number):
    """
    Copy the build filed to deploy folder
    TODO: Support remote deploy location(Cloud .etc)
    """
    course_info = {'course_id': course_id, 'number': build_number}
    observer_logger = get_logger(db.session, course_info)
    observer = ShepherdObserver(observer_logger, BrokerClient('apluslms_shepherd.celery_tasks.build.tasks.update_state',
                                                              'celery_state', course_info))
    observer.enter_build()
    observer.shepherd_step_start(BuildStep.DEPLOY)
    # Check the last step
    logger.info("build_repo result %s", build_result)
    if not build_result['code'] == 0:
        logger.error('The build task was failed, aborting the deployment task')
        observer.shepherd_step_end(BuildStep.DEPLOY, BuildState.CANCELED)
        return {'code': 5, 'msg': 'The clone task was failed or aborted, aborting the build task'}
    # Check is there has a newer version in the queue.If true, cancel the task and start cleaning
    number_list = get_current_build_number_list()
    if int(build_number) < max(number_list):
        logger.warning("Already have newer version in the task queue, task with build number %s aborted.", build_number)
        observer.shepherd_step_end(BuildStep.DEPLOY, BuildState.CANCELED)
        return {'code': 5,
                'msg': "Newer version in the task queue, task with build number {} aborted. Cleaning the local "
                       "repo".format(build_number)}
    log = "The repo has been build, deploying the course, course key: %s, branch: %s" % (course_key, instance_key)
    observer.shepherd_msg(BuildStep.DEPLOY, BuildState.RUNNING, log)
    try:
        build_path = os.path.join(base_path, 'builds', course_key, instance_key, build_number, "_build")
        deploy_path = os.path.join(deploy_base_path, course_key, instance_key, build_number)
        shutil.move(build_path, deploy_path)
    except (FileNotFoundError, OSError, IOError) as why:
        log = 'Error: %', why.strerror
        logger.error(log)
        observer.shepherd_msg(BuildStep.DEPLOY, BuildState.FAILED, log)
        observer.shepherd_step_end(BuildStep.DEPLOY, BuildState.FAILED)
        return {'code': 1, 'msg': 'Error when deploying files'}
    log = "Successfully moved files to deployment folder."
    observer.shepherd_msg(BuildStep.DEPLOY, BuildState.RUNNING, log)
    observer.shepherd_step_end(BuildStep.DEPLOY, BuildState.SUCCESS)
    return {'code': 0, 'msg': log}


@celery.task
def clean(res, base_path, course_id, course_key, instance_key, build_number):
    """
    Clean the generated working tree.
    """
    course_info = {'course_id': course_id, 'number': build_number}
    observer_logger = get_logger(db.session, course_info)
    observer = ShepherdObserver(observer_logger, BrokerClient('apluslms_shepherd.celery_tasks.build.tasks.update_state',
                                                              'celery_state', course_info))
    observer.done()
    observer.shepherd_step_start(BuildStep.CLEAN)
    logger.warning('Cleaning repo')
    path = os.path.join(base_path, 'builds', course_key, instance_key, build_number)
    try:
        log = "Local work tree of build number %s deleted" % build_number
        observer.shepherd_msg(BuildStep.CLEAN, BuildState.RUNNING, log)
        logger.warning(log)
        shutil.rmtree(path)
        observer.shepherd_msg(BuildStep.CLEAN, BuildState.RUNNING, "Worktree cleaned, keep bare repo.")
        observer.shepherd_step_end(BuildStep.CLEAN, BuildState.SUCCESS)
        return {'code': 0, 'msg': 'Worktree cleaned.'}
    except (FileNotFoundError, IOError, OSError) as why:
        logger.info('Error: %s', why.strerror)
        observer.shepherd_msg(BuildStep.CLEAN, BuildState.FAILED, why.strerror)
        observer.shepherd_step_end(BuildStep.CLEAN, BuildState.FAILED)
        return {'code': 1, 'msg': 'Error when cleaning local worktree files,'}


@celery.task
def error_handler(uuid):
    result = AsyncResult(uuid)
    exc = result.get(propagate=False)
    logger.warning('Task %s raised exception: %s\n%s', uuid, exc, result.traceback)
