from flask import Blueprint, render_template
from flask_login import login_required, current_user

from apluslms_shepherd import db
from apluslms_shepherd.courses.models import CourseInstance
from apluslms_shepherd.build.models import Build

main_bp = Blueprint('main', __name__)


class FrontendBuild(object):
    def __init__(self, instance_id, number, course_key, instance_key, action, state):
        self.instance_id = instance_id
        self.instance_key = instance_key
        self.course_key = course_key
        self.number = number
        self.current_state = None if state is None else state.name
        self.current_action = None if action is None else action.name


@main_bp.route('/', methods=['GET'])
@login_required
def main_page():
    instances = CourseInstance.query.all()
    sorted_build_entries = Build.query.order_by(Build.number.desc())
    newest_builds = [
        FrontendBuild(instance_id=instance.id,
                      instance_key=instance.instance_key,
                      course_key=instance.course_key,
                      number=0 if len(sorted_build_entries.filter_by(instance_id=instance.id).all()) is 0
                      else sorted_build_entries.filter_by(instance_id=instance.id).first().number,
                      state=None if len(sorted_build_entries.filter_by(instance_id=instance.id).all()) is 0
                      else sorted_build_entries.filter_by(instance_id=instance.id).first().state,
                      action=None if len(sorted_build_entries.filter_by(instance_id=instance.id).all()) is 0
                      else sorted_build_entries.filter_by(instance_id=instance.id).first().action
                      )
        for instance in instances
    ]
    return render_template('main.html', user=current_user, instances=newest_builds)
