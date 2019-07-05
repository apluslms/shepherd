import os
import subprocess
from datetime import datetime
from urllib.parse import quote

from cryptography.hazmat.backends import default_backend as crypto_default_backend
from cryptography.hazmat.primitives import serialization as crypto_serialization

from apluslms_shepherd.repos.models import GitRepository, State


def verify_key_pair(key_path, git_origin, logger):
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

    if pubkey_from_private_key != repo.public_key:
        repo.state = State.NO_MATCHING_PAIR
        repo.save()
        logger.error(
            'Public key in database and public key generated from private key is not matched, validation failed')
        return False
    logger.info('Key pair of repository with url %s is validated', git_origin)
    logger.info('Validating key with remote git server.')
    proc = subprocess.Popen(["ssh-agent", "sh", "-c", "ssh-add %s; ssh -T git@version.aalto.fi" % private_key_path],
                            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    o, e = proc.communicate()
    logger.info('Output: ' + o.decode('ascii'))
    logger.info('code: ' + str(proc.returncode))
    if proc.returncode != 0:
        logger.error('Error:' + o.decode('ascii'))
        repo.state = State.NO_ACCESS_TO_REMOTE
        repo.save()
        return False
    repo.last_validation = datetime.utcnow()
    repo.state = State.VALID
    repo.save()
    return True
