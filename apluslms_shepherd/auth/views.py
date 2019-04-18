from flask import (Blueprint, render_template)
from flask_login import login_required, current_user

auth_bp = Blueprint('auth', __name__, url_prefix='/auth/')


@login_required
@auth_bp.route('success/', methods=['GET'])
def auth_success():
    return render_template('login_success.html', user=current_user)
