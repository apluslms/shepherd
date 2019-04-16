from flask import Blueprint
from flask_login import login_required

course_bp = Blueprint('courses', __name__, url_prefix='/courses/')

@login_required
@course_bp.route('/', methods=['GET'])
def list_course():
    pass

@login_required
@course_bp.route('add/', methods=['POST'])
def add_course():
    pass

@login_required
@course_bp.route('delete/<course_id>/', methods=['POST'])
def del_course():
    pass