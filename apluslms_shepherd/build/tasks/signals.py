from datetime import datetime

from celery.signals import task_prerun, task_postrun, task_failure, before_task_publish
from celery.utils.log import get_task_logger
from celery.worker.control import revoke

from apluslms_shepherd.build.models import Build, BuildStep, BuildState
from apluslms_shepherd.courses.models import CourseInstance
from apluslms_shepherd.extensions import celery, db

logger = get_task_logger(__name__)

task_step_mapping = {'build_repo': BuildStep.BUILD,
                     'pull_repo': BuildStep.CLONE,
                     'clean': BuildStep.CLEAN,
                     'deploy': BuildStep.DEPLOY}

build_tasks = ['pull_repo', 'build_repo', 'deploy', 'clean']


# For some reason this func is not working if in signal.py. Other signal handling functions works fine
@before_task_publish.connect(sender='apluslms_shepherd.build.tasks.tasks.pull_repo')
def clone_task_before_publish(sender=None, headers=None, body=None, **kwargs):
    """
    information about task are located in headers for task messages
    Only be triggered when publish the "pull_repo" task
    """
    # using the task protocol version 2.
    info = headers if 'task' in headers else body
    logger.warning('before_task_publish for task id {info[id]}'.format(
        info=info,
    ))
    # Get course key and instance_key from the header
    res = eval(headers['argsrepr'])
    course_key = res[-3]
    instance_key = res[-2]
    current_build_number = res[-1]
    logger.warning('course_key:{}, instance_key:{}'.format(course_key, instance_key))
    ins = CourseInstance.query.filter_by(course_key=course_key, instance_key=instance_key).first()
    if ins is None:
        logger.warning('No such course instance in the database')
        revoke(info["id"], terminate=True)
        return
    build = Build(course_id=ins.id, number=current_build_number, start_time=datetime.utcnow(), result=BuildState.NONE)
    db.session.add(build)
    db.session.commit()
    logger.warning('clone_log')
    logger.warning('Task sent')
    logger.warning('Current state sent to frontend')


@task_prerun.connect
def task_prerun(task_id=None, sender=None, *args, **kwargs):
    """
    Triggered when take is about to run
    """
    # information about task are located in headers for task messages
    # using the task protocol version 2.
    if sender.__name__ not in build_tasks:
        return
    logger.warning(sender.__name__ + ' pre_run')
    step = task_step_mapping[sender.__name__]
    instance_key = kwargs['args'][-2]
    course_key = kwargs['args'][-3]
    log_txt = 'task_prerun for task id {}'.format(task_id)
    logger.info(log_txt)
    log_txt = 'course_key:{}, instance_key:{}'.format(course_key, instance_key)
    logger.info(log_txt)
    with celery.app.app_context():
        # Get course instance by course key and instance key
        ins = CourseInstance.query.filter_by(course_key=course_key, instance_key=instance_key).first()
        # If no such instance in database, stop the task
        if ins is None:
            logger.error('No such course instance in the database')
            revoke(task_id, terminate=True)
            return
        log_txt = 'Task {} for course_key:{}, instance_key:{} starts running, current step: {}'.format(
            sender.__name__, course_key,
            instance_key, step.name)
        logger.info(log_txt)
        # Send the state to frontend


@task_postrun.connect
def task_postrun(task_id=None, sender=None, task_result=None, retval=None, *args, **kwargs):
    """
    Triggered when task is finished, in this step , save the task result to database.
    """
    # information about task are located in headers for task messages
    # using the task protocol version 2.
    if sender.__name__ not in build_tasks:
        return
    logger.warning(sender.__name__ + ' post_run')
    step = task_step_mapping[sender.__name__]
    instance_key = kwargs['args'][-2]
    course_key = kwargs['args'][-3]
    if retval['code'] == 0:
        task_result = BuildState.SUCCESS
    elif retval['code'] == 5:
        task_result = BuildState.CANCELED
    else:
        task_result = BuildState.FAILED
    log_text = 'task id {} with course_key: {}, instance_key: {}, step:{} finished. result: {}'.format(task_id,
                                                                                                       course_key,
                                                                                                       instance_key,
                                                                                                       step.name,
                                                                                                       task_result.name)
    logger.info(log_text)


@task_failure.connect
def task_failure(task_id=None, sender=None, *args, **kwargs):
    """
    Triggered when task is failed
    """
    if sender.__name__ not in build_tasks:
        return
    logger.warning(sender.__name__ + ' task_failure')
    logger.info('task_failure for task id {}'.format(
        task_id
    ))
    instance_key = kwargs['args'][-2]
    course_key = kwargs['args'][-3]
    step = task_step_mapping[sender.__name__]
    with celery.app.app_context():
        logger.warning('failed')
        log_text = 'task_failed for task id {}, course_key: {}, instance_key: {} at step {}. result: {}'.format(task_id,
                                                                                                                course_key,
                                                                                                                instance_key,
                                                                                                                step.name,
                                                                                                                BuildState.FAILED.name)
        logger.error(log_text)
