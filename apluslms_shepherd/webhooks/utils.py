from celery import chain
from sqlalchemy import desc

from apluslms_shepherd import config
from apluslms_shepherd.build.models import Build
from apluslms_shepherd.celery_tasks.build.tasks import pull_repo, build_repo, clean, deploy


def schedule_build(repository_url, branch, instance):
    base_path = config.DevelopmentConfig.COURSE_REPO_BASEPATH
    current_build_number = 0 if Build.query.filter_by(instance_id=instance.id).count() is 0 \
        else Build.query.filter_by(instance_id=instance.id).order_by(
        desc(Build.number)).first().number
    pull_s = pull_repo.s(base_path, repository_url, branch, instance.course_key, instance.instance_key,
                         str(current_build_number + 1))
    build_s = build_repo.s(base_path, instance.course_key, instance.instance_key, str(current_build_number + 1))
    deploy_s = deploy.s(config.DevelopmentConfig.COURSE_DEPLOYMENT_PATH, base_path, instance.course_key,
                        instance.instance_key, str(current_build_number + 1))
    clean_s = clean.s(base_path, instance.course_key,
                      instance.instance_key, str(current_build_number + 1))
    return chain(pull_s, build_s, deploy_s, clean_s)()
