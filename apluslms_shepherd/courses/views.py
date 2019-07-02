# standard libs
import logging
from json import dumps

# 3rd party libs
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, abort, Response
from flask_login import login_required, current_user
from sqlalchemy.exc import SQLAlchemyError

# from this project
from apluslms_shepherd.auth.models import User
from apluslms_shepherd.build.models import BuildLog
from apluslms_shepherd.celery_tasks.repos.tasks import clean_unused_repo
from apluslms_shepherd.courses.forms import CourseForm
from apluslms_shepherd.courses.models import CourseInstance, db
from apluslms_shepherd.groups.forms import GroupForm
from apluslms_shepherd.groups.models import (
    Group,
    PermType,
    CreateCoursePerm,
    ManageCoursePerm,
    CourseOwnerType,
)
from apluslms_shepherd.groups.utils import (
    group_slugify,
    PERMISSION_LIST,
    role_permission,
    course_instance_create_perm,
    course_instance_manage_perm,
    course_instance_admin_perm,
    course_instance_create_check,
)
from apluslms_shepherd.repos.models import GitRepository

course_bp = Blueprint('courses', __name__, url_prefix='/courses/')
logger = logging.getLogger(__name__)


@course_bp.route('', methods=['GET'])
@login_required
@role_permission.require(http_exception=403)
def list_course():
    own_course_instances = (db.session.query(CourseInstance)
                            .join(CourseInstance.owners)
                            .filter(Group.members.any(User.id == current_user.id)))

    git_origins = list(dict.fromkeys([c.git_origin for c in own_course_instances]))
    course_instances = (db.session.query(CourseInstance)
                            .filter(CourseInstance.git_origin.in_(git_origins))
                            .order_by(CourseInstance.course_key).all())

    return render_template('courses/course_list.html', user=current_user, 
                           courses=course_instances,
                           own_course_instances=own_course_instances)


@course_bp.route('create/', methods=['GET', 'POST'])
@login_required
@role_permission.require(http_exception=403)
@course_instance_create_perm
def add_course(**kwargs):
    
    identity_groups = kwargs['identity_groups']
    
    owner_groups = Group.query.filter(Group.members.any(id=current_user.id)).all()
    form = CourseForm(request.form)
    form.identity.choices += [(g.id, group_slugify(g.name, g.parent)) for g in identity_groups]
    form.owner_group.choices = [(g.id, group_slugify(g.name, g.parent)) for g in owner_groups]
    group_form = GroupForm(request.form)
    group_form.permissions.choices = [v for v in PERMISSION_LIST if v != ('courses', 'create courses')]
    
    if request.method == 'POST' and form.validate():

        if not course_instance_create_check(form):
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
        course_admin_perm = ManageCoursePerm(course_instance=new_course,group=owner_group,
                                             type=CourseOwnerType.admin)
    
        db.session.add(new_course)
        db.session.add(course_admin_perm)
        repository = GitRepository.query.filter(GitRepository.origin == form.git_origin.data).one_or_none()
        if repository is None:
            new_repository = GitRepository(origin=form.git_origin.data)
            new_repository.save()
        else:
            new_course.git_repository = repository
        db.session.commit()
        flash('New course added.')
        
        return redirect('/courses/')
    return render_template('courses/course_create.html', form=form, group_form=group_form)


@course_bp.route('edit/<course_key>/<instance_key>/', methods=['GET', 'POST'])
@login_required
@role_permission.require(http_exception=403)
@course_instance_admin_perm
def edit_course(course_key, instance_key, **kwargs):
    # Get course from db
    course = CourseInstance.query.filter_by(course_key=course_key, instance_key=instance_key)
    form = CourseForm(request.form, obj=course.first())
    # Get the options of identity groups
    identity_groups = Group.query.filter(Group.members.any(id=current_user.id),
                                         Group.permissions.any(type=PermType.courses)).all()
    form.identity.choices += [(g.id, group_slugify(g.name, g.parent)) for g in identity_groups]
    # Set a default value for owner group to make form validated (owner groups are not edited here)
    form.owner_group.data = -1

    if request.method == 'POST' and form.validate():
        # Check whether the course key match the naming rule
        course_perm = CreateCoursePerm.query.filter_by(group_id=form.identity.data).one_or_none()
        if not course_perm:
            flash('Please choose a valid identity group')
            return redirect(url_for('.edit_course', course_key=course_key, instance_key=instance_key))
        if not course_perm.pattern_match(form.course_key.data.upper()):
            flash('The course key does not match the naming rule: {}'.format(course_perm.pattern))
            return redirect(url_for('.edit_course', course_key=course_key))
        course.update(dict(
            course_key=form.course_key.data.upper(),
            instance_key=form.instance_key.data,
            branch=form.instance_key.data,
            git_origin=form.git_origin.data,
            secret_token=None if form.secret_token.data == '' else form.secret_token.data,
            config_filename=None if form.config_filename.data == '' else form.secret_token.data,
            name=form.name.data
        ))
        flash('Course edited.')
        db.session.commit()
        return redirect('/courses/')
    return render_template('courses/course_edit.html', form=form)


@course_bp.route('delete/<course_key>/<instance_key>/', methods=['POST'])
@login_required
@role_permission.require(http_exception=403)
@course_instance_admin_perm
def del_course_instance(course_key, instance_key, **kwargs):

    course_instance = kwargs['course_instance']
    repo = GitRepository.query.filter_by(origin=course_instance.git_origin).one_or_none()
    repo_number_before_del = 0
    if repo is None:
        logger.error("No matching repo in the database")
    else:
        repo_number_before_del = repo.courses.count()
    db.session.delete(course_instance)
    BuildLog.query.filter_by(instance_id=course_instance.id).delete()
    db.session.commit()
    if repo_number_before_del == 1:
        # start delete celery task
        clean_unused_repo.delay(course_instance.git_origin)
    flash('Instance with key: ' + instance_key + ' belonging to course with key: ' + course_key + ' has been deleted.')
    return redirect('/courses/')

# -------------------------------------------------------------------------------------------------#
# Ownership management


@course_bp.route('<course_key>/<instance_key>/owners/', methods=['GET'])
@login_required
@role_permission.require(http_exception=403)
def owners_list(course_key, instance_key):
    """Get all the owner groups of a course  
    """
    # groups = (db.session.query(Group) 
    #                     .join(CourseInstance.owners)
    #                     .filter(CourseInstance.course_key == course_key,
    #                             CourseInstance.instance_key == instance_key).all())
    perms = (db.session.query(ManageCoursePerm) 
                       .join(ManageCoursePerm.course_instance)
                       .filter(CourseInstance.course_key == course_key,
                               CourseInstance.instance_key == instance_key).all())

    group_array = []

    for perm in perms:
        group_obj = {'id': perm.group.id,
                     'name': group_slugify(perm.group.name, perm.group.parent),
                     'owner_type':perm.type.name}
        group_array.append(group_obj)

    return jsonify({'owner_groups': group_array})


@course_bp.route('<course_key>/<instance_key>/owners/remove/', methods=['POST'])
@login_required
@role_permission.require(http_exception=403)
@course_instance_admin_perm
def owner_remove(course_key, instance_key, **kwargs):
    """Remove an owner group
    """
    course_instance = kwargs['course_instance']

    group_id = request.args.get('group_id')
    group = db.session.query(Group).filter_by(id=group_id).one_or_none()
    manage_course_perm = (db.session.query(ManageCoursePerm)
                                    .filter_by(course_instance=course_instance,
                                               group=group).one_or_none())

    # If the group is the only admin group of the course, it can not be removed
    if manage_course_perm and manage_course_perm.type == CourseOwnerType.admin:
        count_admin = (db.session.query(ManageCoursePerm)
                                 .filter_by(course_instance=course_instance,
                                            type=CourseOwnerType.admin).count())
        if count_admin == 1:
            error_message = dumps({'message': 'The only admin group could not be removed'})
            abort(Response(error_message, 500))

    course_instance.owners.remove(group)
    db.session.delete(manage_course_perm)

    try:
        db.session.commit()
    except SQLAlchemyError as e:
        db.session.rollback()
        error_message = dumps({'message': 'Error occurs and could not remove the owner, Error:%s' % e})
        abort(Response(error_message, 501))

    return jsonify(status='success')


@course_bp.route('<course_key>/<instance_key>/add_owners/options/', methods=['GET'])
@login_required
@role_permission.require(http_exception=403)
def add_owner_list(course_key, instance_key):
    """Get all the possible owner groups could be added for a course
    """
    course_instance = (db.session.query(CourseInstance)
                         .join(CourseInstance.owners)
                         .filter(CourseInstance.course_key == course_key,
                                 CourseInstance.instance_key == instance_key)
                         .filter(Group.members.any(User.id == current_user.id)).one_or_none())
    if not course_instance:
        error_message = dumps({'message': 'The course instance does not exist under the user'})
        abort(Response(error_message, 501))

    owner_groups = course_instance.owners
    groups = [g for g in current_user.groups if g not in owner_groups]

    group_array = []

    for group in groups:
        group_obj = {'id': group.id,
                     'name': group_slugify(group.name, group.parent)}
        group_array.append(group_obj)

    return jsonify({'owner_options': group_array})


@course_bp.route('<course_key>/<instance_key>/owners/add/', methods=['POST'])
@login_required
@role_permission.require(http_exception=403)
@course_instance_admin_perm
def owner_add(course_key, instance_key, **kwargs):
    """add a owner group
    """
    course_instance = kwargs['course_instance']

    group_id = request.args.get('group_id')
    owner_type = request.args.get('owner_type')
    group = db.session.query(Group).filter_by(id = group_id).one_or_none()

    manage_course_perm = ManageCoursePerm(course_instance=course_instance, group=group,
                                          type=CourseOwnerType[owner_type])
    
    try:
        course_instance.owners.append(group)
        db.session.add(manage_course_perm)
        db.session.commit() 
    except SQLAlchemyError as e:
        db.session.rollback()
        error_message = dumps({'message': 'Error occurs and could not remove the owner. Error:%s' % e})
        abort(Response(error_message, 501))

    return jsonify(status='success')
