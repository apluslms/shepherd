import subprocess

from celery.utils.log import get_task_logger
from celery.signals import before_task_publish, task_prerun, after_task_publish, task_postrun, task_success, \
    task_failure, task_received
from datetime import datetime

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
           ins.branch]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    o, e = proc.communicate()
    logger.info('Output: ' + o.decode('ascii'))
    logger.info('code: ' + str(proc.returncode))
    # Store current task id in db
    return o.decode('ascii')


@celery.task(bind=True, default_retry_delay=10)
def build_repo(self):
    pass


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
        task_id=info["id"]+'-PUBLISH',
        course_key=course_key,
        instance_key=instance_key,
        start_time=now,
        status=States.PUBLISH,
        action=Action.CLONE
    )
    print('build_log')

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
