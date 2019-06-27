import os
import shutil

from celery.utils.log import get_task_logger

from apluslms_shepherd import config
from apluslms_shepherd.extensions import celery, db
from apluslms_shepherd.repos.models import GitRepository

logger = get_task_logger(__name__)


@celery.task
def clean_unused_repo(origin):
    """
    Clean the local bare git repository after the last course which is using the repo has been deleted.
    Also delete database entry of this repo.
    """
    logger.info("Start cleaning local git repository")
    repo_path = os.path.join(config.DevelopmentConfig.COURSE_REPO_BASEPATH, origin.split('/')[-1])
    if os.path.exists(repo_path):
        shutil.rmtree(repo_path)
        logger.warning("Local bare repo at %s is deleted" % repo_path)
    else:
        logger.warning("Cannot find local repo at %s." % repo_path)
    # Start deleting from database
    logger.info("Start cleaning database")
    repo_in_db = GitRepository.query.filter(GitRepository.origin == origin).one_or_none()
    if repo_in_db is None:
        logger.warning("Cannot find entry with git origin %s in the database, task aborting" % origin)
        return 1
    else:
        db.session.delete(repo_in_db)
        db.session.commit()
        logger.warning("Database entry with origin: %s has been deleted" % origin)
    return 0
