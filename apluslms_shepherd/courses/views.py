import logging
from json import dumps

from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, abort, Response
from flask_login import login_required, current_user
from sqlalchemy.exc import SQLAlchemyError

from apluslms_shepherd.auth.models import User
from apluslms_shepherd.build.models import BuildLog
from apluslms_shepherd.celery_tasks.repos.tasks import clean_unused_repo
from apluslms_shepherd.courses.forms import CourseForm
from apluslms_shepherd.courses.models import CourseInstance, db
from apluslms_shepherd.groups.forms import GroupForm
from apluslms_shepherd.groups.models import Group, PermType, CreateCoursePerm, \
    ManageCoursePerm, CourseOwnerType
from apluslms_shepherd.groups.utils import group_slugify, PERMISSION_LIST, \
    role_permission, course_instance_create_perm, \
    course_instance_admin_perm
from apluslms_shepherd.repos.models import GitRepository

course_bp = Blueprint('courses', __name__, url_prefix='/courses/')
logger = logging.getLogger(__name__)


@course_bp.route('', methods=['GET'])
@login_required
@role_permission.require(http_exception=403)
def list_course():
    all_courses = CourseInstance.query.all()

    return render_template('courses/course_list.html', user=current_user, courses=all_courses)


@course_bp.route('create/', methods=['GET', 'POST'])
@login_required
@role_permission.require(http_exception=403)
@course_instance_create_perm
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
        exists = CourseInstance.query.filter(CourseInstance.course_key == form.course_key.data.upper(),
                                             CourseInstance.instance_key == form.instance_key.data).first()
        if exists:
            flash('Course key %s and instance key %s already exists.' % (
                form.course_key.data.upper(), form.instance_key.data))
        else:
            new_course = CourseInstance(course_key=form.course_key.data.upper(),
                                        instance_key=form.instance_key.data,
                                        branch=form.instance_key.data,
                                        git_origin=form.git_origin.data,
                                        secret_token=None if form.secret_token.data == '' else form.secret_token.data,
                                        config_filename=None if form.config_filename.data == '' else form.secret_token.data,
                                        name=form.name.data)
            owner_group = Group.query.filter(Group.id == form.owner_group.data).one_or_none()
            new_course.owners.append(owner_group)
            course_admin_perm = ManageCoursePerm(course_instance=new_course, group=owner_group,
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
    git_origin_prev = course.first().git_origin
    form = CourseForm(request.form, obj=course.first())
    # Get the options of identity groups
    identity_groups = Group.query.filter(Group.members.any(id=current_user.id),
                                         Group.permissions.any(type=PermType.courses)).all()
    form.identity.choices += [(g.id, group_slugify(g.name, g.parent)) for g in identity_groups]
    # The label is changes according to whether user is edit a course or creating a course,
    # When editing a course, it should be changed to follows, or it will be "First instance origin"
    if request.method == 'POST' and form.validate():
        # Check whether the course key match the naming rule
        course_perm = CreateCoursePerm.query.filter_by(group_id=form.identity.data).one_or_none()
        if not course_perm:
            flash('Please choose a valid identity group')
            return redirect(url_for('.edit_course', course_key=course_key, instance_key=instance_key))
        if not course_perm.pattern_match(form.course_key.data.upper()):
            flash('The course key does not match the naming rule: {}'.format(course_perm.pattern))
            return redirect(url_for('.edit_course', course_key=course_key))
        git_origin_new = form.git_origin.data
        course.update(dict(
            course_key=form.course_key.data.upper(),
            instance_key=form.instance_key.data,
            branch=form.instance_key.data,
            git_origin=git_origin_new,
            secret_token=None if form.secret_token.data == '' else form.secret_token.data,
            config_filename=None if form.config_filename.data == '' else form.secret_token.data,
            name=form.name.data
        ))
        flash('Course edited.')
        db.session.commit()
        logger.info('Course edited')
        # Check if has change on origin
        if git_origin_new != git_origin_prev:
            # Delete old, if old repo becomes an orphan repository.
            if CourseInstance.query.filter_by(git_origin=git_origin_prev).one_or_none() is None:
                logger.info(
                    'This edit makes the repository %s becomes an orphan repository, cleaning this repository.' % git_origin_prev)
                clean_unused_repo.delay(git_origin_prev)
            # Create new, is this new repo is not in db yet.
            if GitRepository.query.filter_by(origin=git_origin_new).one_or_none() is None:
                logger.info('This new repository is not exists in database,add it to database')
                GitRepository(origin=git_origin_new).save()
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
        logger.info(
            'The repository %s becomes an orphan repository after deleting the course instance, cleaning this repository.' % course_instance.git_origin)
        clean_unused_repo.delay(course_instance.git_origin)
    flash('Instance with key: ' + instance_key + ' belonging to course with key: ' + course_key + ' has been deleted.')
    return redirect('/courses/')


# -------------------------------------------------------------------------------------------------#
# Ownership management

@course_bp.route('<course_key>/<instance_key>/owners/', methods=['GET'])
@login_required
@role_permission.require(http_exception=403)
def owners_list(course_key, instance_key, **kwargs):
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
        groupObj = {'id': perm.group.id,
                    'name': group_slugify(perm.group.name, perm.group.parent),
                    'owner_type': perm.type.name}
        group_array.append(groupObj)

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
    if not (manage_course_perm and manage_course_perm.type == CourseOwnerType.admin and len(
            course_instance.owners) <= 1):
        course_instance.owners.remove(group)
        db.session.delete(manage_course_perm)
    else:
        error_message = dumps({'message': 'The only admin group could not be removed'})
        abort(Response(error_message, 500))

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
def add_owner_list(course_key, instance_key, **kwargs):
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
        groupObj = {'id': group.id,
                    'name': group_slugify(group.name, group.parent)}
        group_array.append(groupObj)

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
    group = db.session.query(Group).filter_by(id=group_id).one_or_none()

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
