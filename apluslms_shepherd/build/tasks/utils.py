import subprocess
from os.path import exists, join, isfile
from urllib.parse import quote

from apluslms_roman import ProjectConfig, Engine
from apluslms_roman.configuration import ProjectConfigError
from apluslms_roman.settings import GlobalSettings
from apluslms_yamlidator.validator import ValidationError, render_error
from celery.utils.log import get_task_logger

from apluslms_shepherd import celery
from apluslms_shepherd.build.models import BuildStep, BuildState
from apluslms_shepherd.courses.models import CourseInstance
from apluslms_shepherd.observer.observer import ShepherdObserver

logger = get_task_logger(__name__)


def get_current_build_number_list():
    inspector = celery.control.inspect()
    task_list = inspector.active()
    task_build_number_list = []
    for each_worker in task_list.values():
        task_build_number_list = [int(eval(str(each_task['args']).replace('\r', '\\r').replace('\n', '\\n'))[-1]) for
                                  each_task in each_worker]
    return task_build_number_list


def bare_clone(base_path, origin, course, instance, branch, number, key_path, observer):
    """
    Clone orr update bare repo
    :param base_path:
    :param origin: git origin
    :param branch: git branch
    :param course: course key
    :param instance: instance_key
    :param number: build_number
    :param key_path: path to private key
    :param observer: observer instance
    :return: boolean, if is succeeded
    """
    has_private_key = isfile(key_path)
    course_id = CourseInstance.query.filter_by(course_key=course, instance_key=instance).first().id
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
        observer.state_update(course_id, number, BuildStep.CLONE, BuildState.RUNNING,
                              proc.stdout.decode('utf-8'))
        if proc.returncode != 0:
            logger.error(proc.returncode, proc.stdout)
            return proc.returncode
    else:
        logger.info('No local repo can be found, cloning from remote at ' + origin)
        proc = subprocess.run(['git', 'clone', '--bare', origin], env=env, cwd=base_path,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        logger.info(proc.stdout)
        observer.state_update(course_id, number, BuildStep.CLONE, BuildState.RUNNING,
                              proc.stdout.decode('utf-8'))
        if proc.returncode != 0:
            logger.error('Error in cloning, program terminated. Code:', str(proc.returncode))
            return proc.returncode
        if not exists(repo_folder):
            logger.error('Cannot find cloned repo, terminated')
            return 1

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


def roman_build(base_path, course_id, course_key, instance_key, build_number, config_filename=None):
    shepherd_builder_observer = ShepherdObserver([course_id, build_number, BuildStep.BUILD.name, None, ""])
    source_path = join(base_path, 'builds', course_key, instance_key, build_number)
    if not exists(source_path):
        logger.error("Cannot find source file for building at %s", source_path)
        return 1
    # Get config
    try:
        project_config = ProjectConfig.find_from(source_path)
    except ValidationError as e:
        logger.error(render_error(e))
        return 1
    except ProjectConfigError as e:
        logger.error('Invalid project configuration: %s', e)
        return 1
    # Get global settings
    try:
        global_settings = GlobalSettings.load(
            config_filename if config_filename is not None else GlobalSettings.get_config_path(), allow_missing=True)
    except ValidationError as e:
        logger.error(render_error(e))
        return 1
    except OSError as e:
        logger.error(str(e))
        return 1
    # Get engine
    try:
        engine = Engine(settings=global_settings)
    except ImportError:
        logger.error("Unable to find backend %s", str(global_settings))
        return 1
    builder = engine.create_builder(project_config, shepherd_builder_observer)
    if not project_config.steps:
        logger.error("Nothing to build.")
        return 1
    try:
        result = builder.build()
    except KeyError as err:
        logger.error("No step named %s", err.args[0])
        return 1
    except IndexError as err:
        logger.error("Index %s is out of range. There are %d steps. Indexing begins ar 0.", err.args[0],
                     len(project_config.steps))
    return result.code


def slugify(git_origin):
    non_utf = ['@', '/', ':']
    ret = git_origin.replace('_', '__')
    for each in non_utf:
        ret = ret.replace(each, '_')
    return ret
