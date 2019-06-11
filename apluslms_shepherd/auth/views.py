from flask import current_app,session
from apluslms_shepherd.extensions import db
from flask import (Blueprint, render_template, redirect, flash)
from flask_login import login_required, current_user, logout_user
from flask_principal import AnonymousIdentity,identity_changed

auth_bp = Blueprint('auth', __name__, url_prefix='/auth/')


@auth_bp.route('success/', methods=['GET'])
@login_required
def auth_success():
    return render_template('login_success.html', user=current_user)


@auth_bp.route('logout/', methods=['GET'])
@login_required
def logout():
    logout_user()
    # Remove session keys set by Flask-Principal
    for key in ('identity.name', 'identity.auth_type'):
        session.pop(key, None)

    # Tell Flask-Principal the user is anonymous
    identity_changed.send(current_app._get_current_object(),
                          identity=AnonymousIdentity())
    flash("User logout.")
    return redirect('https://plus.cs.hut.fi/')
