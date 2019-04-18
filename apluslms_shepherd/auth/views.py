from flask import (Blueprint, render_template, redirect, flash)
from flask_login import login_required, current_user, logout_user

auth_bp = Blueprint('auth', __name__, url_prefix='/auth/')



@auth_bp.route('success/', methods=['GET'])
@login_required
def auth_success():
    return render_template('login_success.html', user=current_user)


@auth_bp.route('logout/', methods=['GET'])
@login_required
def logout():
    logout_user()
    flash("User logout.")
    return redirect('https://plus.cs.hut.fi/')