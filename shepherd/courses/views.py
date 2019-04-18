from flask import Blueprint, render_template, request, flash, redirect
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError

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
        try:
            db.session.add(new_course)
            db.session.commit()
            flash('New course added.')
        except IntegrityError:
            flash('Course key already exists.')
        return redirect('/courses/')
    return render_template('course_create.html', form=form)


@login_required
@course_bp.route('create/<course_id>/', methods=['GET', 'POST'])
def add_course_instance(course_id):
    course_repo = CourseRepository.query.filter_by(key=course_id)
    form = InstanceForm(request.form, obj=CourseInstance(git_origin=course_repo.first().git_origin))
    if form.validate() and request.method == 'POST':
        new_course_instance = CourseInstance(key=form.key.data, git_origin=form.git_origin.data, branches=form.branches.data, course_key=course_id)
        try:
            db.session.add(new_course_instance)
            db.session.commit()
            flash('New course instance added for course ' + course_id + '!')
        except IntegrityError:
            flash('Course instance already exists.')
        return redirect('/courses/')
    return render_template('instance_create.html', form=form, course=course_repo)


@login_required
@course_bp.route('edit/<course_id>/', methods=['GET', 'POST'])
def edit_course(course_id):
    course = CourseRepository.query.filter_by(key=course_id, owner=current_user.id)
    course_instances = CourseInstance.query.filter_by(course_key=course_id)
    if course is None:
        flash('There is no such course under this user')
        return redirect('/courses/')
    else:
        form = CourseForm(request.form, obj=course.first())
        form.change_all.label = "Would like to change the git repo of " \
                                + str(course_instances.count())\
                                + " instance(s) belong to this course as well?"
        if form.validate() and request.method == 'POST':
            course.update(dict(
                key=form.key.data,
                git_origin=form.git_origin.data,
                name=form.name.data,
            ))
            if form.change_all.data:
                course_instances.update(dict(git_origin= form.git_origin.data))
                flash('Course edited, as well as the instances')
            else:
                flash('Course edited.')
            db.session.commit()
            return redirect('/courses/')
    return render_template('course_edit.html', form=form, instances_num=course_instances.count())


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
                git_origin=form.git_origin.data,
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


@login_required
@course_bp.route('delete/<course_id>/<instance_id>/', methods=['POST'])
def del_course_instance(course_id, instance_id):
    instance = CourseInstance.query.filter_by(course_key=course_id, key=instance_id).first()
    if instance is None:
        flash('There is no such course under this user')
    else:
        db.session.delete(instance)
        db.session.commit()
        flash('Instance with key: '+instance_id+' belonging to course with key: '+course_id+' has been deleted.')
    return redirect('/courses/')