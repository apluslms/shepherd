import logging

from flask import Blueprint, render_template
from flask_login import login_required, current_user

from apluslms_shepherd.groups.utils import role_permission
from apluslms_shepherd.repos.models import GitRepository

repo_bp = Blueprint('repos', __name__, url_prefix='/repos/')
logger = logging.getLogger(__name__)


@repo_bp.route('', methods=['GET'])
@login_required
@role_permission.require(http_exception=403)
def list_repos():
    all_repos = GitRepository.query.all()
    return render_template('repos/repo_list.html', user=current_user, repos=all_repos)
