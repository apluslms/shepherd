from flask import (Blueprint, render_template, request, flash, abort)
from flask_login import current_user

webhooks_bp = Blueprint('webhooks', __name__, url_prefix='/hooks/')


@webhooks_bp.route('update/', methods=['POST'])
def update():
    update_type = request.headers.get('X-Gitlab-Event', False)
    data = request.get_json() or {}

    if not update_type:
        abort(403, 'No X-Gitlab-Event header given')
    print(data)
    if 'repository' in data and 'name' in data['repository']:
        print("Matching repo: {}".format(data['repository']))

    return "hi"
