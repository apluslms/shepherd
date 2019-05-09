from celery.utils.log import get_task_logger
from celery.signals import before_task_publish, task_prerun, after_task_publish, task_postrun, task_success, \
    task_failure
from datetime import datetime

from celery.worker.control import revoke
from sqlalchemy import desc
from sqlalchemy.orm import session

from apluslms_shepherd.build.models import Build, BuildLog, States, Action
from apluslms_shepherd.celery_tasks.tasks import build_repo
from apluslms_shepherd.courses.models import CourseInstance
from apluslms_shepherd.extensions import celery, db

logger = get_task_logger(__name__)

'''
Triggered when take is about to run
'''


@task_prerun.connect
def task_prerun(task_id=None, sender=None, *args, **kwargs):
    # information about task are located in headers for task messages
    # using the task protocol version 2.
    print(sender.__name__ + 'pre_run')
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
        ins = CourseInstance.query.filter_by(course_key=course_key, key=instance_key).first()
        # If no such instance in database, stop the task
        if ins is None:
            logger.error('No such course instance inthe database')
            revoke(task_id, terminate=True)
            return
        # Get the current build.
        build = Build.query.filter_by(instance_id=ins.id, number=current_build_number).first()
        if sender.__name__ is 'build_repo':
            new_log_entry = BuildLog(
                instance_id=ins.id,
                start_time=now,
                number=current_build_number,
                action=Action.BUILD
            )
            db.session.add(new_log_entry)
        # We don't catch the task publish signal of Build. That's because even this two tasks run in sequence, the build
        # will be published before clone task runs, so the state in of Build table will be changed too early.
        # In this case, we create the BuildLog and change the state in the Build table of Build task in this function
        build.action = Action.CLONE if sender.__name__ is 'pull_repo' else Action.BUILD
        build.state = States.RUNNING
        db.session.commit()


'''
Triggered when task is finished
'''


@task_postrun.connect
def task_postrun(task_id=None, sender=None, state=None, retval=None, *args, **kwargs):
    # information about task are located in headers for task messages
    # using the task protocol version 2.
    print(sender.__name__ + 'post_run')
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
        instance_id = CourseInstance.query.filter_by(course_key=course_key, key=instance_key).first().id
        # add end time for build entry and buildlog entry, change build state
        print('finished')
        now = datetime.utcnow()
        build = Build.query.filter_by(instance_id=instance_id,
                                      number=current_build_number).first()
        # Get current build_log, filter condition "action" is different according to the task
        build_log = BuildLog.query.filter_by(instance_id=instance_id,
                                             number=current_build_number,
                                             action=Action.CLONE if sender.__name__ is 'pull_repo' else Action.BUILD).first()
        # Write output to db
        build_log.log_text = retval
        # The state code is in the beginning, divided with main part by "|"
        build.state = States.FINISHED if retval.split('|')[0] is '0' else States.FAILED
        # If this is the end of clone task, no need to set end time for Build entry, because the whole task is not
        # done yet(Still have Build and Deployment left)
        build.end_time = now if sender.__name__ is 'build_repo' else None
        # Set end time for current build phrase
        build_log.end_time = now
        db.session.commit()


'''
Triggered when task is failed
'''


@task_failure.connect
def task_failure(task_id=None, sender=None, *args, **kwargs):
    print(sender.__name__ + 'task_failure')
    logger.info('task_failure for task id {}'.format(
        task_id
    ))
    current_build_number = kwargs['args'][-1]
    instance_key = kwargs['args'][-2]
    course_key = kwargs['args'][-3]
    with celery.app.app_context():
        instance_id = CourseInstance.query.filter_by(course_key=course_key, key=instance_key).first().id

        # add end time for build entry and buildlog entry, change build state
        print('finished')
        now = datetime.utcnow()
        # get current build and build_log from db
        build = Build.query.filter_by(instance_id=instance_id,
                                      number=current_build_number).first()
        build_log = BuildLog.query.filter_by(instance_id=instance_id,
                                             number=current_build_number,
                                             action=Action.CLONE if sender.__name__ is 'pull_repo' else Action.BUILD)\
            .first()
        # Change the state to failed, set the end time
        build.state = States.FAILED
        build.end_time = now
        build_log.end_time = now
        db.session.commit()
