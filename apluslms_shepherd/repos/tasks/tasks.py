import os
import shutil
from datetime import datetime, timedelta

from celery.utils.log import get_task_logger
from cryptography.hazmat.backends import default_backend as crypto_default_backend
from cryptography.hazmat.primitives import serialization as crypto_serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from apluslms_shepherd import config
from apluslms_shepherd.build.tasks.utils import slugify
from apluslms_shepherd.extensions import celery, db
from apluslms_shepherd.repos.models import GitRepository
from apluslms_shepherd.repos.tasks.utils import verify_key_pair

logger = get_task_logger(__name__)

task_result_mapping = {True: 1, False: 0}
validate_logging_mapping = {True: 'Validation succeed', False: 'Validation failed'}


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
        logger.info("Local bare repo at %s is deleted", repo_path)
    else:
        logger.warning("Cannot find local repo at %s. No build has been executed or error in filesystem", repo_path)
    # Start deleting from database
    logger.info("Start cleaning database")
    repo_in_db = GitRepository.query.filter(GitRepository.origin == origin).one_or_none()
    private_key_path = repo_in_db.private_key_path
    if repo_in_db is None:
        logger.warning("Cannot find entry with git origin %s in the database, task aborting", origin)
        return 1
    else:
        db.session.delete(repo_in_db)
        db.session.commit()
        shutil.rmtree(private_key_path)
        logger.warning("Database entry with origin: %s has been deleted",  origin)
    return 0


@celery.task
def generate_deploy_key(key_path, git_origin):
    repos = GitRepository.query.filter_by(origin=git_origin)
    if repos.count() == 0:
        logger.error("No match course find for this key generation, exiting...")
        return -1
    logger.info('Start generating file')
    final_path = os.path.join(key_path, slugify(git_origin))
    private_key_path = os.path.join(final_path, "private.pem")
    # Generate private key
    key = rsa.generate_private_key(
        backend=crypto_default_backend(),
        public_exponent=65537,
        key_size=2048
    )
    private_key = key.private_bytes(
        crypto_serialization.Encoding.PEM,
        crypto_serialization.PrivateFormat.PKCS8,
        crypto_serialization.NoEncryption())
    # Generate Public key
    public_key = key.public_key().public_bytes(
        crypto_serialization.Encoding.OpenSSH,
        crypto_serialization.PublicFormat.OpenSSH
    )
    logger.info('Generated public key is %s', public_key.decode('utf-8'))
    repos.first().public_key = public_key.decode('utf-8')
    db.session.commit()
    # Write keys to the local
    if not os.path.exists(final_path):
        os.makedirs(final_path, 0o777)
    with open(private_key_path, "wb") as f:
        f.write(private_key)
    os.chmod(private_key_path, 0o600)
    celery.add_periodic_task(10.0, validate_deploy_key.s(key_path, git_origin),
                             name='validate_%s' % slugify(git_origin))
    celery.send_task("apluslms_shepherd.repos.tasks.tasks.validate_deploy_key", args=[key_path, git_origin])
    return 0


@celery.task
def validate_deploy_key(key_path, git_origin):
    ret = task_result_mapping[verify_key_pair(key_path, git_origin, logger)]
    return ret


@celery.task
def validate_deploy_key_scheduled(key_path):
    logger.info("Validation task started, Scanning all existing repo under %s", key_path)
    for each in GitRepository.query.all():
        if each.last_validation is None:
            logger.info("Found repository with url %s needs verification,"
                        "Never validated",
                        each.origin,
                        )
            res = verify_key_pair(key_path, each.origin, logger)
            logger.warning(validate_logging_mapping[res])
        period = datetime.utcnow() - each.last_validation
        if period > timedelta(days=0, hours=0, seconds=10):
            logger.info("Found repository with url %s needs verification,"
                        "last validation is %s days %s seconds ago",
                        each.origin,
                        period.days,
                        period.seconds
                        )
            res = verify_key_pair(key_path, each.origin, logger)
            logger.warning(validate_logging_mapping[res])
