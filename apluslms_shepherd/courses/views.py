from flask import Blueprint, render_template, request, flash, redirect,url_for
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError

from apluslms_shepherd.courses.forms import CourseForm, InstanceForm
from apluslms_shepherd.courses.models import CourseRepository, CourseInstance, db
from apluslms_shepherd.groups.models import Group,PermType,CreateCoursePerm
from apluslms_shepherd.groups.utils import course_perm,group_slugify
course_bp = Blueprint('courses', __name__, url_prefix='/courses/')


@course_bp.route('', methods=['GET'])
@login_required
def list_course():
    all_courses = CourseRepository.query.all()
    return render_template('course_list.html', user=current_user, courses=all_courses)


@course_bp.route('create/', methods=['GET', 'POST'])
@login_required
@course_perm
def add_course():
    groups = Group.query.filter(Group.members.any(id=current_user.id),
                            Group.permissions.any(type=PermType.courses)).all()
    form = CourseForm(request.form)
    form.owner.choices =  [(g.id, group_slugify(g.name,g.parent_id)) for g in groups]
    form.git_origin.label = "First Instance Git Origin"
    if form.validate() and request.method == 'POST':
        course_perm = CreateCoursePerm.query.filter_by(group_id=form.owner.data).one_or_none()
        if not course_perm.pattern_match(form.key.data.upper()):
            flash('The course key does not match the naming rule ',str(course_perm.pattern))
            redirect(url_for('.add_course'))
        else:    
            new_course = CourseRepository(key=form.key.data.upper(),
                                        name=form.name.data,
                                        owner_id=form.owner.data)
            # new_course.owner = Group.query.filter(Group.id == form.owner.data).one_or_none()
            try:
                db.session.add(new_course)
                db.session.commit()
                flash('New course added.')
            except IntegrityError:
                flash('Course key already exists.')
            # Part of first instance info provided in the form
            new_instance = CourseInstance(course_key=form.key.data, branch=form.branch.data, key=form.instance_key.data,
                                        git_origin=form.git_origin.data)
            # Also add a new instance with the course, the instance kay and course key is combined primary key of the
            # CourseInstance model
            try:
                db.session.add(new_instance)
                db.session.commit()
                flash('New course added with a new instance under this course')
            except IntegrityError:
                flash('New course added, but Instance key already exists.')
            return redirect('/courses/')
    return render_template('course_create.html', form=form)


@course_bp.route('create/<course_key>/', methods=['GET', 'POST'])
@login_required
def add_course_instance(course_key):
    course_repo = CourseRepository.query.filter_by(key=course_key)
    last_instance = CourseInstance.query.filter_by(course_key=course_key).first()
    form = InstanceForm(request.form, obj=CourseInstance(git_origin=last_instance.git_origin))

    if form.validate() and request.method == 'POST':
        # Using the git repo of first instance as the default repo
        new_course_instance = CourseInstance(key=form.key.data,
                                             git_origin=form.git_origin.data,
                                             branch=form.branch.data,
                                             course_key=course_key,
                                             secret_token=None if form.secret_token.data == '' else form.secret_token.data,
                                             config_filename=None if form.config_filename.data == '' else form.config_filename.data
                                             )
        print(db.session.query(CourseInstance.key).filter_by(course_key=course_key, key=form.key.data).scalar())
        if db.session.query(CourseInstance.key).filter_by(course_key=course_key, key=form.key.data).scalar() is not None:
            flash('Course instance already exists.')
        else:
            try:
                db.session.add(new_course_instance)
                db.session.commit()
                flash('New course instance added for course ' + course_key + '!')
            except IntegrityError:
                flash('Course instance already exists.')
        return redirect('/courses/')
    return render_template('instance_create.html', form=form, course=course_repo)


@course_bp.route('edit/<course_key>/', methods=['GET', 'POST'])
@login_required
def edit_course(course_key):
    course = CourseRepository.query.filter_by(key=course_key)
    course_instances = CourseInstance.query.filter_by(course_key=course_key)
    if course is None:
        flash('There is no such course under this user')
        return redirect('/courses/')
    elif current_user not in course.first().owner.members:
        flash('Permission Denied')
        return redirect('/courses/')
    else:
        form = CourseForm(request.form, obj=course.first())
        groups = Group.query.filter(Group.members.any(id=current_user.id),
                            Group.permissions.any(type=PermType.courses)).all()
        form.owner.choices =  [(g.id, group_slugify(g.name,g.parent_id)) for g in groups]
        # The label is changes according to whether user is edit a course or creating a course,
        # When editing a course, it should be changed to follows, or it will be "First instance origin"
        form.git_origin.label = "New Git Origin for all instance"
        form.change_all.label = "Would like to change the git repo of " \
                                + str(course_instances.count()) \
                                + " instance(s) belong to this course as well?"
        if form.validate() and request.method == 'POST':
            course_perm = CreateCoursePerm.query.filter_by(group_id=form.owner.data).one_or_none()
            if not course_perm.pattern_match(form.key.data.upper()):
                flash('The course key does not match the naming rule')
                return redirect(url_for('.edit_course',course_key=course_key))

            course.update(dict(
                key=form.key.data,
                name=form.name.data,
                owner_id = form.owner.data
            ))
            # If checkbox clicked
            if form.change_all.data:
                course_instances.update(dict(git_origin=form.git_origin.data))
                flash('Course edited, as well as the instances')
            else:
                flash('Course edited.')
            db.session.commit()
            return redirect('/courses/')
    return render_template('course_edit.html', form=form, instances_num=course_instances.count())


@course_bp.route('edit/<course_key>/<instance_key>/', methods=['GET', 'POST'])
@login_required
def edit_instance(course_key, instance_key):
    instance = CourseInstance.query.filter_by(key=instance_key, course_key=course_key)
    if instance is None:
        flash('There is no such instance under this course')
        return redirect('/courses/')
    else:
        form = InstanceForm(request.form, obj=instance.first())
        if form.validate() and request.method == 'POST':
            instance.update(dict(
                key=form.key.data,
                git_origin=form.git_origin.data,
                branch=form.branch.data,
                config_filename=form.config_filename.data
            ))
            db.session.commit()
            flash('Instance edited.')
            return redirect('/courses/')
    return render_template('instance_edit.html', form=form)


@course_bp.route('delete/<course_key>/', methods=['POST'])
@login_required
def del_course(course_key):
    course =CourseRepository.query.filter(CourseRepository.key==course_key).first()
    if course is None:
        flash('There is no such course under this user')
    elif current_user not in course.owner.members:
        flash('Permission Denied')
    else:
        # The delete is cascade, the instance will be deleted as well.
        db.session.delete(course)
        db.session.commit()
        flash('Course with key: ' + course_key + ' name: ' + course.name + ' has been deleted.')
    return redirect('/courses/')


@course_bp.route('delete/<course_key>/<instance_key>/', methods=['POST'])
@login_required
def del_course_instance(course_key, instance_key):
    instance = CourseInstance.query.filter_by(course_key=course_key, key=instance_key).first()
    if instance is None:
        flash('There is no such course under this user')
    else:
        db.session.delete(instance)
        db.session.commit()
        flash(
            'Instance with key: ' + instance_key + ' belonging to course with key: ' + course_key + ' has been deleted.')
    return redirect('/courses/')


@course_bp.route('logs/<instance_id>/', methods=['GET'])
@login_required
def instance_log(instance_id):
    instance = CourseInstance.query.filter_by(id=instance_id).first()
    if instance is None:
        flash('No such instance in the database, please refresh the page.')
        redirect('')
    render_template('instance_log.html', instance=instance)
