from datetime import datetime

from celery.signals import task_prerun, task_postrun, task_failure, before_task_publish
from celery.utils.log import get_task_logger
from celery.worker.control import revoke

from apluslms_shepherd.build.models import Build, BuildLog, BuildAction, BuildState
from apluslms_shepherd.celery_tasks.build.utils import update_frontend
from apluslms_shepherd.courses.models import CourseInstance
from apluslms_shepherd.extensions import celery, db

logger = get_task_logger(__name__)

task_action_mapping = {'build_repo': BuildAction.BUILD,
                       'pull_repo': BuildAction.CLONE,
                       'clean': BuildAction.CLEAN,
                       'deploy': BuildAction.DEPLOY}

build_tasks = ['pull_repo', 'build_repo', 'deploy', 'clean']


# For some reason this func is not working if in signal.py. Other signal handling functions works fine
@before_task_publish.connect(sender='apluslms_shepherd.celery_tasks.build.tasks.pull_repo')
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
    now = datetime.utcnow()
    ins = CourseInstance.query.filter_by(course_key=course_key, instance_key=instance_key).first()
    if ins is None:
        logger.warning('No such course instance in the database')
        revoke(info["id"], terminate=True)
        return
    # Create new build entry and buildlog entry
    build = Build(instance_id=ins.id, start_time=now,
                  state=BuildState.PUBLISH,
                  action=BuildAction.CLONE, number=current_build_number)
    new_log_entry = BuildLog(
        instance_id=ins.id,
        start_time=now,
        number=current_build_number,
        action=BuildAction.CLONE
    )
    logger.warning('clone_log')
    db.session.add(new_log_entry)
    db.session.add(build)
    db.session.commit()
    logger.warning('Task sent')
    update_frontend(ins.id, current_build_number, BuildAction.CLONE, BuildState.PUBLISH,
                    "-------------------------------------------------New Build Start-------------------------------------------------\n"
                    "Instance with course_key:{}, instance_key:{} entering task queue, this is build No.{}".format(
                        course_key,
                        instance_key,
                        current_build_number))
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
    now = datetime.utcnow()
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
        # Get the current build.
        build = Build.query.filter_by(instance_id=ins.id, number=current_build_number).first()
        # Build log of 'pull_repo' is already created in the publish signal handler.
        if sender.__name__ is not 'pull_repo':
            new_log_entry = BuildLog(
                instance_id=ins.id,
                start_time=now,
                number=current_build_number,
                action=task_action_mapping[sender.__name__]
            )
            db.session.add(new_log_entry)
        # We don't catch the task publish signal of Build. That's because even this two tasks run in sequence, the build
        # will be published before clone task runs, so the state in of Build table will be changed too early.
        # In this case, we create the BuildLog and change the state in the Build table of Build task in this function
        build.action = task_action_mapping[sender.__name__]
        build.state = BuildState.RUNNING
        db.session.commit()
        # Send the state to frontend
        update_frontend(ins.id, current_build_number, task_action_mapping[sender.__name__], BuildState.RUNNING,
                        'Task {} for course_key:{}, instance_key:{} starts running'.format(sender.__name__, course_key,
                                                                                           instance_key))


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
    now = datetime.utcnow()
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
        now = datetime.utcnow()
        build = Build.query.filter_by(instance_id=instance_id,
                                      number=current_build_number).first()
        # Get current build_log, filter condition "action" is different according to the task
        build_log = BuildLog.query.filter_by(instance_id=instance_id,
                                             number=current_build_number,
                                             action=task_action_mapping[sender.__name__]).first()
        # Write output to db
        # The state code is in the beginning, divided with main part by "|"
        if isinstance(retval, str):
            build_log.log_text = retval
            build.state = BuildState.FINISHED if str(retval).split('|')[0] == '0' else BuildState.FAILED
        else:
            logger.warning('return is not str or int')
            build.state = BuildState.FAILED
            build_log.log_text = str(retval)
        # If this is the end of clone task, no need to set end time for Build entry, because the whole task is not
        # done yet(Still have Build and Deployment left)
        build.end_time = now if sender.__name__ is 'clean' else None
        # Set end time for current build phrase
        build_log.end_time = now
        db.session.commit()
        update_frontend(instance_id, current_build_number, task_action_mapping[sender.__name__], build.state,
                        str(retval).replace('\\r', '\r').replace('\\n', '\n'))


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

        # add end time for build entry and buildlog entry, change build state
        logger.warning('finished')
        now = datetime.utcnow()
        # get current build and build_log from db
        build = Build.query.filter_by(instance_id=instance_id,
                                      number=current_build_number).first()
        build_log = BuildLog.query.filter_by(instance_id=instance_id,
                                             number=current_build_number,
                                             action=task_action_mapping[sender.__name__]).first()
        # Change the state to failed, set the end time
        build.state = BuildState.FAILED
        build.end_time = now
        build_log.end_time = now
        db.session.commit()
        update_frontend(instance_id, current_build_number, task_action_mapping[sender.__name__], BuildState.FAILED,
                        'Task' + sender.__name__ + 'is Failed')
