import os
from datetime import datetime
from urllib.parse import quote

from celery.utils.log import get_task_logger
from cryptography.hazmat.backends import default_backend as crypto_default_backend
from cryptography.hazmat.primitives import serialization as crypto_serialization

from apluslms_shepherd.repos.models import GitRepository

logger = get_task_logger(__name__)


def verify_key_pair(key_path, git_origin):
    private_key_path = os.path.join(key_path, quote(git_origin), 'private.pem')
    with open(private_key_path, "rb") as key_file:
        private_key = crypto_serialization.load_pem_private_key(
            key_file.read(),
            password=None,
            backend=crypto_default_backend()
        )
    pubkey_from_private_key = private_key.public_key().public_bytes(
        crypto_serialization.Encoding.OpenSSH,
        crypto_serialization.PublicFormat.OpenSSH
    ).decode('utf-8')
    repo = GitRepository.query.filter_by(origin=git_origin).first_or_404()
    if repo is None:
        logger.error('No matching repository in database is found, validation failed')
        return False
    else:
        if pubkey_from_private_key == repo.public_key:
            logger.info('Key pair of repository with url %s is validated', git_origin)
            repo.last_validation = datetime.utcnow()
            repo.save()
        else:
            logger.error(
                'Public key in database and public key generated from private key is not matched, validation failed')
            return False
    return True
