import subprocess
from os.path import exists, join, isfile
from urllib.parse import quote

from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


def bare_clone(base_path, origin, course, instance, branch, number, key_path):
    """
    Clone orr update bare repo
    :param base_path:
    :param origin: git origin
    :param branch: git branch
    :param course: course key
    :param instance: instance_key
    :param number: build_number
    :param key_path: path to private key
    :return: boolean, if is succeeded
    """
    has_private_key = isfile(key_path)
    if has_private_key:
        logger.info("Private key detected on {}.".format(key_path))
        env = dict(SSH_ASKPASS="echo", GIT_TERMINAL_PROMPT="0",
                   GIT_SSH_COMMAND="ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i {}".format(
                       key_path))
    else:
        logger.info("Private key cannot be found.")
        env = dict(SSH_ASKPASS="echo", GIT_TERMINAL_PROMPT="0")
    repo_folder = join(base_path, quote(origin).split('/')[-1])
    # Check is using clone or fetch
    if exists(repo_folder):
        logger.info("Find local repo, update")
        proc = subprocess.run(['git', 'fetch', 'origin', branch + ':' + branch], env=env, cwd=repo_folder,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        logger.info(proc.stdout)
        if proc.returncode != 0:
            logger.error('Error in fetching update, program terminated. Code:', str(proc.returncode))
            return proc.returncode
    else:
        logger.info('No local repo can be found, cloning from remote at ' + origin)
        proc = subprocess.run(['git', 'clone', '--bare', origin], env=env, cwd=base_path,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        logger.info(proc.stdout)
        if proc.returncode != 0:
            logger.error('Error in cloning, program terminated. Code:', str(proc.returncode))
            return proc.returncode
        if not exists(repo_folder):
            logger.error('Cannot find cloned repo, terminated')
            return -1

    # Generate worktree
    logger.info("Generating worktree.")
    worktree_path = join(base_path, 'builds', course, instance, number)
    proc = subprocess.run(['git', 'worktree', 'add', '-f', worktree_path, branch], env=env, cwd=repo_folder,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    logger.info(proc.stdout)
    if proc.returncode != 0:
        logger.error('Error in generating worktree, program terminated. Code:', str(proc.returncode))
        return proc.returncode
    proc = subprocess.run("git submodule init && git submodule update --depth 1", shell=True, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, cwd=worktree_path)
    logger.info(proc.stdout)
    if proc.returncode != 0:
        logger.error('Error in generating worktree, program terminated. Code:', str(proc.returncode))
        return proc.returncode
    return 0
