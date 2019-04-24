import json

from apluslms_shepherd.webhooks.pipeline import GitPipeline
from flask import (Blueprint, render_template, request, flash, abort)
from flask_login import current_user

webhooks_bp = Blueprint('webhooks', __name__, url_prefix='/hooks/')


@webhooks_bp.route('pushed/', methods=['POST'])
def pushed():
    update_type = request.headers.get('X-Gitlab-Event')
    gitlab_token = request.headers.get('X-GitLab-Token')
    data = json.loads(request.data.decode('utf-8'))
    if not update_type:
        abort(400, 'No X-Gitlab-Event header given')
    if 'repository' in data and 'url' in data['repository']:
        print("Matching repo: {}".format(data['repository']))
        git_ssh_url = data['repository']['git_ssh_url']
        git_http_url = data['repository']['git_http_url']
        print("Git Push detected: git_ssh_url:{}, git_http_url:{}".format(git_ssh_url, git_http_url))
        pipline = GitPipeline()
    else:
        abort(400, "Invalid payload")


    return 'hi'
