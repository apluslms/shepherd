from flask import Blueprint, render_template, request, flash, redirect
from flask_login import login_required, current_user
from shepherd.courses.forms import CourseForm, InstanceForm
from shepherd.courses.models import CourseRepository, CourseInstance, db

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
        new_course = CourseRepository(key=form.key.data,
                                      git_origin=form.git_origin.data,
                                      name=form.name.data,
                                      owner=current_user.id)
        db.session.add(new_course)
        db.session.commit()
        flash('New course added.')
        return redirect('/courses/')
    return render_template('course_create.html', form=form)


@login_required
@course_bp.route('create/<course_id>/', methods=['GET', 'POST'])
def add_course_instance(course_id):
    form = InstanceForm(request.form)
    if form.validate() and request.method == 'POST':
        new_course_instance = CourseInstance(key=form.key.data, branches=form.branches.data, course_key=course_id)
        db.session.add(new_course_instance)
        db.session.commit()
        flash('New course instance added for course '+course_id+'!')
        return redirect('/courses/')
    return render_template('instance_create.html', form=form, course_id=course_id)


@login_required
@course_bp.route('edit/<course_id>/', methods=['GET', 'POST'])
def edit_course(course_id):
    course = CourseRepository.query.filter_by(key=course_id, owner=current_user.id)
    if course is None:
        flash('There is no such course under this user')
        return redirect('/courses/')
    else:
        form = CourseForm(request.form, obj=course.first())
        if form.validate() and request.method == 'POST':
            course.update(dict(
                key=form.key.data,
                git_origin=form.git_origin.data,
                name=form.name.data,
            ))
            db.session.commit()
            flash('Course edited.')
            return redirect('/courses/')
    return render_template('course_edit.html', form=form)


@login_required
@course_bp.route('edit/<course_id>/<instance_id>/', methods=['GET', 'POST'])
def edit_instance(course_id, instance_id):
    instance = CourseInstance.query.filter_by(key=instance_id, course_key=course_id)
    if instance is None:
        flash('There is no such instance under this course')
        return redirect('/courses/')
    else:
        form = InstanceForm(request.form, obj=instance.first())
        if form.validate() and request.method == 'POST':
            instance.update(dict(
                key=form.key.data,
                branches=form.branches.data
            ))
            db.session.commit()
            flash('Instance edited.')
            return redirect('/courses/')
    return render_template('instance_edit.html', form=form)


@login_required
@course_bp.route('delete/<course_id>/', methods=['POST'])
def del_course(course_id):
    course = CourseRepository.query.filter_by(key=course_id, owner=current_user.id).first()
    if course is None:
        flash('There is no such course under this user')
    else:
        db.session.delete(course)
        db.session.commit()
        flash('Course with key: '+course_id+' name: '+course.name+' has been deleted.')
    return redirect('/courses/')
