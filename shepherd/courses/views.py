from flask import Blueprint, render_template, request, flash, redirect
from flask_login import login_required, current_user
from shepherd.courses.forms import CourseForm
from shepherd.courses.models import CourseRepository, CourseRepositoryUpdate, db

course_bp = Blueprint('courses', __name__, url_prefix='/courses/')


@login_required
@course_bp.route('', methods=['GET'])
def list_course():
    all_courses = CourseRepository.query.all()
    return render_template('course_list.html', user=current_user, courses=all_courses)


@login_required
@course_bp.route('create/', methods=['GET', 'POST'])
def add_course():
    form = CourseForm(request.form)
    if form.validate() and request.method == 'POST':
        print(form.key)
        new_course = CourseRepository(key=form.key.data,
                                      git_branch=form.git_branch.data,
                                      git_origin=form.git_origin.data,
                                      name=form.name.data,
                                      owner=current_user.id)
        db.session.add(new_course)
        db.session.commit()
        flash('New course added.')
        return redirect('/courses/')
    return render_template('course_create.html', form=form)





@login_required
@course_bp.route('delete/<course_id>/', methods=['POST'])
def del_course():
    pass