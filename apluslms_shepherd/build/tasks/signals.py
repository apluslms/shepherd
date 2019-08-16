from celery.signals import task_prerun, task_postrun, task_failure, before_task_publish
from celery.utils.log import get_task_logger
from celery.worker.control import revoke

from apluslms_shepherd.build.models import Build, BuildStep, BuildState
from apluslms_shepherd.build.tasks import build_observer
from apluslms_shepherd.courses.models import CourseInstance
from apluslms_shepherd.extensions import celery

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
    build_observer.update_database(ins.id, current_build_number, BuildStep.CLONE, BuildState.PUBLISH)
    logger.warning('clone_log')
    logger.warning('Task sent')
    build_observer.enter_prepare()
    build_observer.state_update(ins.id, current_build_number, BuildStep.CLONE, BuildState.PUBLISH,
                                "-------------------------------------------------New Build Start-------------------------------------------------\n "
                                "Instance with course_key:{}, instance_key:{} entering task queue, this is build No.{} \n".format(
                                    course_key,
                                    instance_key,
                                    current_build_number))
    logger.warning('Current state sent to frontend')
    build_observer.step_pending(BuildStep.CLONE)


@task_prerun.connect
def task_prerun(task_id=None, sender=None, *args, **kwargs):
    """
    Triggered when take is about to run
    """
    # information about task are located in headers for task messages
    # using the task protocol version 2.
    if sender.__name__ not in build_tasks:
        return
    if sender.__name__ == 'pull_repo':
        build_observer.enter_prepare()
    else:
        build_observer.enter_build()
    build_observer.step_running(task_step_mapping[sender.__name__])
    logger.warning(sender.__name__ + ' pre_run')
    current_build_number = kwargs['args'][-1]
    instance_key = kwargs['args'][-2]
    course_key = kwargs['args'][-3]
    logger.info('task_prerun for task id {}'.format(
        task_id
    ))
    logger.info('course_key:{}, instance_key:{}'.format(course_key, instance_key))
    with celery.app.app_context():
        # Get course instance by course key and instance key
        ins = CourseInstance.query.filter_by(course_key=course_key, instance_key=instance_key).first()
        # If no such instance in database, stop the task
        if ins is None:
            logger.error('No such course instance inthe database')
            revoke(task_id, terminate=True)
            return
        build_observer.update_database(ins.id, current_build_number, task_step_mapping[sender.__name__],
                                       BuildState.RUNNING)
        # Send the state to frontend
        build_observer.state_update(ins.id, current_build_number, task_step_mapping[sender.__name__],
                                    BuildState.RUNNING,
                                    'Task {} for course_key:{}, instance_key:{} starts running\n'.format(
                                        sender.__name__, course_key,
                                        instance_key))
        build_observer.step_running(task_step_mapping[sender.__name__])


@task_postrun.connect
def task_postrun(task_id=None, sender=None, state=None, retval=None, *args, **kwargs):
    """
    Triggered when task is finished
    """
    # information about task are located in headers for task messages
    # using the task protocol version 2.
    if sender.__name__ not in build_tasks:
        return
    logger.warning(sender.__name__ + ' post_run')
    current_build_number = kwargs['args'][-1]
    instance_key = kwargs['args'][-2]
    course_key = kwargs['args'][-3]
    logger.info('task_postrun for task id {}'.format(
        task_id
    ))
    logger.info('course_key:{}, instance_key:{}'.format(course_key, instance_key))
    with celery.app.app_context():
        # Get the instance id
        instance_id = CourseInstance.query.filter_by(course_key=course_key, instance_key=instance_key).first().id
        # add end time for build entry and buildlog entry, change build state
        logger.warning('finished')
        build = Build.query.filter_by(instance_id=instance_id,
                                      number=current_build_number).first()
        # The state code is in the beginning, divided with main part by "|"
        log_text = retval['msg']
        if retval['code'] == 0:
            state = BuildState.SUCCESS
        elif retval['code'] == 5:
            state = BuildState.CANCELED
        else:
            state = BuildState.FAILED
        build_observer.update_database(instance_id, current_build_number, task_step_mapping[sender.__name__], state,
                                       log_text)
        build_observer.state_update(instance_id, current_build_number, task_step_mapping[sender.__name__],
                                    build.state,
                                    log_text.replace('\\r', '\r').replace('\\n', '\n') + '\n')
        build_observer.step_succeeded(task_step_mapping[sender.__name__])


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
    current_build_number = kwargs['args'][-1]
    instance_key = kwargs['args'][-2]
    course_key = kwargs['args'][-3]
    with celery.app.app_context():
        instance_id = CourseInstance.query.filter_by(course_key=course_key, instance_key=instance_key).first().id

        logger.warning('finished')
        build_observer.update_database(instance_id, current_build_number, task_step_mapping[sender.__name__],
                                       BuildState.SUCCESS, )
        build_observer.state_update(instance_id, current_build_number, task_step_mapping[sender.__name__],
                                    BuildState.FAILED,
                                    'Task {} is Failed.\n'.format(sender.__name__))
        build_observer.step_failed(task_step_mapping[sender.__name__])
