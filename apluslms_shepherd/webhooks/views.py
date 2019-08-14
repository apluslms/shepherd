import json

from flask import Blueprint, request, abort

from apluslms_shepherd import config
from apluslms_shepherd.build.tasks.tasks import pull_repo, build_repo, error_handler
from apluslms_shepherd.courses.models import CourseInstance
from apluslms_shepherd.webhooks.utils import schedule_build

webhooks_bp = Blueprint('webhooks', __name__, url_prefix='/hooks/')

'''
Only support push at moment
'''


@webhooks_bp.route('gitlab/', methods=['POST'])
def gitlab():
    update_type = request.headers.get('X-Gitlab-Event')
    gitlab_token = request.headers.get('X-GitLab-Token')
    data = json.loads(request.data.decode('utf-8'))
    if not update_type:
        abort(400, 'No X-Gitlab-Event header given')
    if str(update_type) != "Push Hook":
        abort(400, "Not a push event")
    if 'ref' and 'repository' in data and 'url' in data['repository']:
        git_branch = data['ref'].split('/')[2]
        git_ssh_url = data['repository']['git_ssh_url']
        git_http_url = data['repository']['git_http_url']
        print("Git Push at GitLab detected: git_ssh_url:{}, git_http_url:{}, on branch {}".format(git_ssh_url,
                                                                                                  git_http_url,
                                                                                                  git_branch))
        instance = CourseInstance.query \
            .filter((CourseInstance.origin == git_ssh_url) | (CourseInstance.origin == git_http_url)) \
            .filter_by(secret_token=gitlab_token, branch=git_branch) \
            .first()
        if instance is None:
            abort(401, "Invalid token or no matching local course instance")
        if config.Config.USE_SSH_FOR_GIT:
            use_url = git_ssh_url
        else:
            use_url = git_http_url
        # Run task
        schedule_build(use_url, git_branch, instance)
    else:
        abort(400, "Invalid payload")
    return 'hi from a+'


'''
Only support push at moment
'''


@webhooks_bp.route('github/', methods=['POST'])
def github_pushed():
    base_path = config.DevelopmentConfig.COURSE_REPO_BASEPATH
    update_type = request.headers.get('X-GitHub-Event')
    token = request.headers.get('X-Hub-Signature')
    data = json.loads(request.data.decode('utf-8'))
    if not update_type:
        abort(400, 'No X-GitHub-Event header given')
    if str(update_type) != "push":
        abort(400, "Not a push event")
    if 'ref' and 'repository' in data and 'url' in data['repository']:
        git_branch = data['ref'].split('/')[2]
        git_ssh_url = data['repository']['ssh_url']
        git_http_url = data['repository']['clone_url']
        print("Git Push at GitLab detected: git_ssh_url:{}, git_http_url:{}, on branch {}".format(git_ssh_url,
                                                                                                  git_http_url,
                                                                                                  git_branch))
        instance = CourseInstance.query \
            .filter((CourseInstance.origin == git_ssh_url) | (CourseInstance.origin == git_http_url)) \
            .filter_by(secret_token=token, branch=git_branch) \
            .first()
        if instance is None:
            print("Invalid token, or no matching local course instance")
            abort(401, "Invalid token or no matching local course instance")

        if config.Config.USE_SSH_FOR_GIT:
            use_url = git_ssh_url
        else:
            use_url = git_http_url

            # Run task
        # pull_s = pull_repo.s(base_path, use_url, git_branch, instance.course_key, instance.key)
        build_s = build_repo.s(base_path, instance.course_key, instance.key)
        pull_repo.apply_async(args=[base_path, use_url, git_branch, instance.course_key, instance.key],
                              link=build_s,
                              link_error=error_handler.s())
    else:
        abort(400, "Invalid payload")
    return 'hi from a+'
