from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, abort, Response
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError
from sqlalchemy import inspect
from json import dumps

from apluslms_shepherd.courses.forms import CourseForm
from apluslms_shepherd.courses.models import CourseInstance, db
from apluslms_shepherd.groups.models import Group, PermType, CreateGroupPerm, CreateCoursePerm,\
    ManageCoursePerm, CourseOwnerType
from apluslms_shepherd.groups.utils import group_slugify,PERMISSION_LIST, \
    role_permission,course_create_perm, course_manage_perm, course_admin_perm

from apluslms_shepherd.auth.models import User
from apluslms_shepherd.groups.views import list_users, add_member
from apluslms_shepherd.groups.views import create_group
from apluslms_shepherd.groups.forms import GroupForm
import logging

course_bp = Blueprint('courses', __name__, url_prefix='/courses/')
logger = logging.getLogger(__name__)


@course_bp.route('', methods=['GET'])
@login_required
@role_permission.require(http_exception=403)
def list_course():
    all_courses = CourseInstance.query.all()

    return render_template('course_list.html', user=current_user, courses=all_courses)


@course_bp.route('create/', methods=['GET', 'POST'])
@login_required
@role_permission.require(http_exception=403)
@course_create_perm
def add_course(**kwargs):
    if 'identity_groups' in kwargs:
        identity_groups = kwargs['identity_groups']
    else:
        identity_groups = Group.query.filter(Group.members.any(id=current_user.id),
                                             Group.permissions.any(type=PermType.courses)).all()
    owner_groups = Group.query.filter(Group.members.any(id=current_user.id)).all()

    form = CourseForm(request.form)
    form.identity.choices += [(g.id, group_slugify(g.name, g.parent)) for g in identity_groups]
    form.owner_group.choices = [(g.id, group_slugify(g.name, g.parent)) for g in owner_groups]
    group_form = GroupForm(request.form)
    group_form.permissions.choices = [v for v in PERMISSION_LIST if v != ('courses', 'create courses')]

    if request.method == 'POST' and form.validate():

        course_perm = CreateCoursePerm.query.filter_by(group_id=form.identity.data).one_or_none()
        if not course_perm:
            flash('Please choose a valid identity')
            return redirect(url_for('.add_course'))

        if not course_perm.pattern_match(form.course_key.data.upper()):
            flash('The course key does not match the naming rule ')
            return redirect(url_for('.add_course'))

        new_course = CourseInstance(course_key=form.course_key.data.upper(),
                                    instance_key=form.instance_key.data,
                                    branch=form.instance_key.data,
                                    git_origin=form.git_origin.data,
                                    secret_token=None if form.secret_token.data == '' else form.secret_token.data,
                                    config_filename=None if form.config_filename.data == '' else form.secret_token.data,
                                    name=form.name.data)
        owner_group = Group.query.filter(Group.id == form.owner_group.data).one_or_none()
        new_course.owners.append(owner_group)
        course_admin_perm = ManageCoursePerm(course=new_course,group=owner_group,
                                            type=CourseOwnerType.admin)
        exists = CourseInstance.query.filter_by(course_key=new_course.course_key, instance_key=new_course.instance_key).all() is not None
        print([i for i in CourseInstance.query.filter_by(course_key=new_course.course_key, instance_key=new_course.instance_key).all()])
        if exists:
            flash('Course key %s and instance key %s already exists.' % (new_course.course_key, new_course.instance_key))
            return redirect('/courses/')
        try:
            db.session.add(new_course)
            db.session.add(course_admin_perm)
            db.session.commit()
            flash('New course added.')
        except IntegrityError:
            flash('Course key already exists.')
        # Also add a new instance with the course, the instance kay and course key is combined primary key of the
        # CourseInstance model
        return redirect('/courses/')
    return render_template('course_create.html', form=form, group_form=group_form)


@course_bp.route('edit/<course_key>/<instance_key>/', methods=['GET', 'POST'])
@login_required
@role_permission.require(http_exception=403)
@course_manage_perm
def edit_course(course_key, instance_key, **kwargs):
    # Get course from db
    course = CourseInstance.query.filter_by(course_key=course_key, instance_key=instance_key)
    form = CourseForm(request.form, obj=course.first())
    # Get the options of identity groups
    identity_groups = Group.query.filter(Group.members.any(id=current_user.id),
                                         Group.permissions.any(type=PermType.courses)).all()
    form.identity.choices += [(g.id, group_slugify(g.name, g.parent)) for g in identity_groups]
    # The label is changes according to whether user is edit a course or creating a course,
    # When editing a course, it should be changed to follows, or it will be "First instance origin"
    form.git_origin.label = "New Git Origin for all instance"
    if request.method == 'POST' and form.validate():
        # Check whether the course key match the naming rule
        course_perm = CreateCoursePerm.query.filter_by(group_id=form.identity.data).one_or_none()
        if not course_perm:
            flash('Please choose a valid identity group')
            return redirect(url_for('.edit_course', course_key=course_key))
        if not course_perm.pattern_match(form.key.data.upper()):
            flash('The course key does not match the naming rule: {}'.format(course_perm.pattern))
            return redirect(url_for('.edit_course', course_key=course_key))
        course.update(dict(
            course_key=form.course_key.data.upper(),
            instance_key=form.instance_key.data.upper,
            branch=form.instance_key.data,
            git_origin=form.git_origin.data,
            secret_token=None if form.secret_token.data == '' else form.secret_token.data,
            config_filename=None if form.config_filename.data == '' else form.secret_token.data,
            name=form.name.data
        ))

        flash('Course edited.')
        db.session.commit()
        return redirect('/courses/')
    return render_template('course_edit.html', form=form)


@course_bp.route('delete/<course_key>/<instance_key>/', methods=['POST'])
@login_required
@role_permission.require(http_exception=403)
@course_manage_perm
def del_course_instance(course_key, instance_key, **kwargs):
    instance = CourseInstance.query.filter_by(course_key=course_key, instance_key=instance_key).first()
    if instance is None:
        flash('There is no such course under this user')
    else:
        db.session.delete(instance)
        db.session.commit()
        flash(
            'Instance with key: ' + instance_key + ' belonging to course with key: ' + course_key + ' has been deleted.')
    return redirect('/courses/')

# -------------------------------------------------------------------------------------------------#
# Ownership management

@course_bp.route('<course_key>/owners/', methods=['GET'])
@login_required
@role_permission.require(http_exception=403)
def owners_list(course_key, **kwargs):
    """Get all the owner groups of a course  
    """
    groups = db.session.query(Group). \
        join(CourseInstance.owners). \
        filter(CourseInstance.course_key == course_key).all()

    groupArray = []

    for group in groups:
        groupObj = {'id': group.id,
                    'name': group_slugify(group.name, group.parent)}
        groupArray.append(groupObj)

    return jsonify({'owner_groups': groupArray})


@course_bp.route('<course_key>/owners/delete/', methods=['POST'])
@login_required
@role_permission.require(http_exception=403)
@course_admin_perm
def owner_remove(course_key,**kwargs):
    """Remove a owner group
    """
    course = kwargs['course']

    group_id = request.args.get('group_id')
    group = db.session.query(Group).filter_by(id=group_id).one_or_none()
    manage_course_perm = db.session.query(ManageCoursePerm).\
                                    filter_by(course=course,group=group).one_or_none()

    if not (manage_course_perm and manage_course_perm.type==CourseOwnerType.admin and len(course.owners)<=1):
        course.owners.remove(group)
        db.session.delete(manage_course_perm)
    else:
        error_message = dumps({'message': 'The only admin group could not be removed'})
        abort(Response(error_message, 500))

    try:
        db.session.commit()
    except:
        db.session.rollback()
        error_message = dumps({'message': 'Error occurs and could not remove the owner'})
        abort(Response(error_message, 501))

    return jsonify(status='success')


@course_bp.route('<course_key>/owners/options/', methods=['GET'])
@login_required
@role_permission.require(http_exception=403)
def add_owner_list(course_key, **kwargs):
    """Get all the possible owner groups could be added for a course
    """
    course = db.session.query(CourseInstance). \
        join(CourseInstance.owners). \
        filter(CourseInstance.course_key == course_key). \
        filter(Group.members.any(User.id == current_user.id)). \
        one_or_none()
    if not course:
        error_message = dumps({'message': 'Error'})
        abort(Response(error_message, 501))

    owner_groups = course.owners
    groups = [g for g in current_user.groups if g not in owner_groups]

    groupArray = []

    for group in groups:
        groupObj = {'id': group.id,
                    'name': group_slugify(group.name, group.parent)}
        groupArray.append(groupObj)

    return jsonify({'owner_options': groupArray})


@course_bp.route('<course_key>/owners/add/', methods=['POST'])
@login_required
@role_permission.require(http_exception=403)
@course_admin_perm
def owner_add(course_key,**kwargs):
    """add a owner group
    """
    course = kwargs['course']

    group_id = request.args.get('group_id')
    owner_type = request.args.get('owner_type')
    group = db.session.query(Group).filter_by(id=group_id).one_or_none()

    manage_course_perm = ManageCoursePerm(course=course,group=group,
                        type=CourseOwnerType[owner_type])
    
    try:
        course.owners.append(group)
        db.session.add(manage_course_perm)
        db.session.commit() 
    except:
        db.session.rollback()
        error_message = dumps({'message': 'Error occurs and could not add the owner'})
        abort(Response(error_message, 501))

    return jsonify(status='success')
