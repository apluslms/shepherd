from flask import Blueprint, jsonify
from apluslms_shepherd.courses.models import CourseInstance
from celery.result import AsyncResult
from apluslms_shepherd.celery_tasks import app

build_bp = Blueprint('result', __name__, url_prefix='/build/')


@build_bp.route('/statue/<course_key>/<instance_key>/', methods=['GET'])
def build_state(course_key, instance_key):
    instance = CourseInstance.query.filter_by(key=instance_key, course_key=course_key).first()
    with app.app_context():
        state_pull = AsyncResult(instance.pull_task_id, app=app)
        state_build = AsyncResult(instance.build_task_id, app=app)
    return jsonify(
        {
            'pull':
                {
                    'state': state_pull.status,
                    'result': state_pull.result
                },

            'build':
                {
                    'state': state_build.status,
                    'result': state_build.result
                }
        }
    )
