
from celery.utils.log import get_task_logger
from celery.signals import before_task_publish, task_prerun, after_task_publish, task_postrun, task_success, \
    task_failure
from datetime import datetime

from apluslms_shepherd.build.models import Build, BuildLog, States, Action
from apluslms_shepherd.extensions import celery, db

logger = get_task_logger(__name__)


@task_prerun.connect
def clone_task_prerun(task_id=None, sender=None, *args, **kwargs):
    # information about task are located in headers for task messages
    # using the task protocol version 2.
    print('pre_run')
    now = datetime.utcnow()
    instance_key = kwargs['args'][-1]
    course_key = kwargs['args'][-2]
    logger.info('task_prerun for task id {}'.format(
        task_id
    ))
    logger.info('course_key:{}, instance_key:{}'.format(course_key, instance_key))
    with celery.app.app_context():
        old_log_entry = BuildLog.query.filter_by(
            task_id=task_id+'-PUBLISH',
            action=Action.CLONE if sender.__name__ is 'pull_repo' else Action.BUILD
        ).first()
        print(old_log_entry)
        old_log_entry.end_time = now
        new_log_entry = BuildLog(
            task_id=task_id+'-RUNNING',
            course_key=course_key,
            instance_key=instance_key,
            start_time=now,
            status=States.RUNNING,
            action=Action.CLONE if sender.__name__ is 'pull_repo' else Action.BUILD
        )
        build = Build.query.filter_by(course_key=course_key, instance_key=instance_key).first()
        if build is None:
            build = Build(course_key=course_key, instance_key=instance_key, start_time=now, status=States.RUNNING,
                          action=Action.CLONE if sender.__name__ is 'pull_repo' else Action.BUILD.CLONE)
            db.session.add(build)
        else:
            build.status = States.RUNNING
        db.session.add(new_log_entry)
        db.session.commit()




@task_postrun.connect
def clone_task_postrun(task_id=None, sender=None, *args, **kwargs):
    # information about task are located in headers for task messages
    # using the task protocol version 2.
    print('post_run')
    now = datetime.utcnow()
    instance_key = kwargs['args'][-1]
    course_key = kwargs['args'][-2]
    logger.info('task_postrun for task id {}'.format(
        task_id
    ))
    logger.info('course_key:{}, instance_key:{}'.format(course_key, instance_key))
    with celery.app.app_context():
        old_log_entry = BuildLog.query.filter_by(
            task_id=task_id+'-RUNNING',
            action=Action.CLONE if sender.__name__ is 'pull_repo' else Action.BUILD
        ).first()
        old_log_entry.end_time = now
        new_log_entry = BuildLog(
            task_id=task_id+'-FINISHED',
            course_key=course_key,
            instance_key=instance_key,
            start_time=now,
            status=States.FINISHED,
            action=Action.CLONE if sender.__name__ is 'pull_repo' else Action.BUILD
        )
        print('finished')
        build = Build.query.filter_by(course_key=course_key, instance_key=instance_key).first()
        build.status = States.FINISHED
        db.session.add(new_log_entry)
        db.session.commit()


@task_failure.connect
def clone_task_failure(task_id=None, sender=None, *args, **kwargs):
    # information about task are located in headers for task messages
    # using the task protocol version 2.
    print('task_failure')
    now = datetime.utcnow()
    logger.info('task_failure for task id {}'.format(
        task_id
    ))
    with celery.app.app_context():
        old_log_entry = BuildLog.query.filter_by(
            task_id=task_id+'-RUNNING',
            action=Action.CLONE if sender.__name__ is 'pull_repo' else Action.BUILD
        ).first()
        old_log_entry.end_time = now
        new_log_entry = BuildLog(
            task_id=task_id+'-FAILURE',
            course_key=old_log_entry.course_key,
            instance_key=old_log_entry.instance_key,
            start_time=now,
            status=States.FAILED,
            action=Action.CLONE if sender.__name__ is 'pull_repo' else Action.BUILD,
            log_text=kwargs['result']
        )
        build = Build.query.filter_by(course_key=old_log_entry.course_key, instance_key=old_log_entry.instance_key).first()
        build.status = States.FAILED
        db.session.add(new_log_entry)
        db.session.commit()