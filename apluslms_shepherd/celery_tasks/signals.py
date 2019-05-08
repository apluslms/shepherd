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
    instance_key = kwargs['args'][-1]
    course_key = kwargs['args'][-2]
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
        # Get the current biggest build number for current instance.
        current_build_number = 0 if Build.query.filter_by(instance_id=ins.id).count() is 0 is None \
            else Build.query.filter_by(instance_id=ins.id).order_by(desc(Build.number)).first().number
        print(current_build_number)
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
    instance_key = kwargs['args'][-1]
    course_key = kwargs['args'][-2]
    logger.info('task_postrun for task id {}'.format(
        task_id
    ))
    logger.info('course_key:{}, instance_key:{}'.format(course_key, instance_key))
    with celery.app.app_context():
        # Get the build number
        instance_id = CourseInstance.query.filter_by(course_key=course_key, key=instance_key).first().id
        current_build_number = 0 if Build.query.filter_by(instance_id=instance_id).count() is 0 \
            else Build.query.filter_by(instance_id=instance_id).order_by(
            desc(Build.number)).first().number
        # add end time for build entry and buildlog entry, change build state
        print('finished')
        now = datetime.utcnow()
        build = Build.query.filter_by(instance_id=instance_id,
                                      number=current_build_number).first()
        # Get current build_log
        build_log = BuildLog.query.filter_by(instance_id=instance_id,
                                             number=current_build_number,
                                             action=Action.CLONE if sender.__name__ is 'pull_repo' else Action.BUILD).first()
        # Write output to db
        build_log.log_text = retval
        build.state = States.FINISHED if retval.split('|')[0] is '0' else States.FAILED
        build.end_time = now if sender.__name__ is 'build_repo' else None
        build_log.end_time = now
        db.session.commit()


'''
Triggered when task is failed
'''


@task_failure.connect
def task_failure(task_id=None, sender=None, *args, **kwargs):
    print(sender.__name__ + 'task_failure')
    now = datetime.utcnow()
    logger.info('task_failure for task id {}'.format(
        task_id
    ))
    instance_key = kwargs['args'][-1]
    course_key = kwargs['args'][-2]
    with celery.app.app_context():
        instance_id = CourseInstance.query.filter_by(course_key=course_key, key=instance_key).first().id
        current_build_number = 0 if Build.query.filter_by(instance_id=instance_id).count() is 0 \
            else Build.query.filter_by(instance_id=instance_id).order_by(
            desc(Build.number)).first().number
        # add end time for build entry and buildlog entry, change build state
        print('finished')
        now = datetime.utcnow()
        # get current build and build_log from db
        build = Build.query.filter_by(course_key=course_key, instance_key=instance_key,
                                      number=current_build_number).first()
        build_log = BuildLog.query.filter_by(course_key=course_key, instance_key=instance_key,
                                             number=current_build_number,
                                             action=Action.CLONE if sender.__name__ is 'pull_repo' else Action.BUILD).first()
        build.state = States.FAILED
        build.end_time = now
        build_log.end_time = now
        db.session.commit()
