from flask import Blueprint, flash, redirect, render_template
from flask_login import login_required, current_user

from apluslms_shepherd.courses.models import CourseInstance

build_log_bp = Blueprint('build_logs', __name__, url_prefix='/logs/')


@build_log_bp.route('<instance_id>/', methods=['GET'])
@login_required
def instance_log(instance_id):
    instance = CourseInstance.query.filter_by(id=instance_id).first()
    if instance is None:
        flash('No such instance in the database, please refresh the page.')
        redirect('')
    return render_template('builds/instance_log.html', instance=instance.__dict__, user=current_user)
