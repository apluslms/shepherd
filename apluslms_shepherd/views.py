from flask import Blueprint, render_template
from flask_login import login_required, current_user

from apluslms_shepherd.build.models import Build
from apluslms_shepherd.courses.models import CourseInstance

main_bp = Blueprint('main', __name__)


class FrontendBuild(object):
    def __init__(self, course_id, number, course_key, instance_key, result):
        self.course_id = course_id
        self.instance_key = instance_key
        self.course_key = course_key
        self.number = number
        self.current_result = None if result is None else result.name


@main_bp.route('/', methods=['GET'])
@login_required
def main_page():
    instances = CourseInstance.query.all()
    sorted_build_entries = Build.query.order_by(Build.number.desc())
    newest_builds = [
        FrontendBuild(course_id=instance.id,
                      instance_key=instance.instance_key,
                      course_key=instance.course_key,
                      number=0 if len(sorted_build_entries.filter_by(course_id=instance.id).all()) is 0
                      else sorted_build_entries.filter_by(course_id=instance.id).first().number,
                      result=None if len(sorted_build_entries.filter_by(course_id=instance.id).all()) is 0
                      else sorted_build_entries.filter_by(course_id=instance.id).first().result,
                      )
        for instance in instances
    ]
    return render_template('main.html', user=current_user, instances=newest_builds)
