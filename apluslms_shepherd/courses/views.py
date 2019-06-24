from flask import Blueprint, render_template, request, flash, redirect,url_for,jsonify,abort,Response
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError
from sqlalchemy import inspect
from json import dumps
from apluslms_shepherd.courses.forms import CourseCreateForm, InstanceForm, CourseEditForm
from apluslms_shepherd.courses.models import CourseRepository, CourseInstance, db
from apluslms_shepherd.groups.models import Group, PermType, CreateGroupPerm, CreateCoursePerm
from apluslms_shepherd.groups.utils import group_slugify,PERMISSION_LIST, \
    role_permission,course_create_perm, course_manage_perm
from apluslms_shepherd.auth.models import User
from apluslms_shepherd.groups.views import list_users,add_member
from apluslms_shepherd.groups.views import create_group
from apluslms_shepherd.groups.forms import GroupForm
course_bp = Blueprint('courses', __name__, url_prefix='/courses/')


@course_bp.route('', methods=['GET'])
@login_required
@role_permission.require(http_exception=403)
def list_course():

    all_courses = CourseRepository.query.all()

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

    owner_groups  = Group.query.filter(Group.members.any(id=current_user.id)).all()

    form = CourseCreateForm(request.form)
    form.identity.choices += [(g.id, group_slugify(g.name,g.parent)) for g in identity_groups]
    form.owner_group.choices = [(g.id, group_slugify(g.name,g.parent)) for g in owner_groups]
    form.git_origin.label = "First Instance Git Origin"

    group_form = GroupForm(request.form)
    group_form.permissions.choices = [v for v in PERMISSION_LIST if v != ('courses','create courses')]  

    if request.method == 'POST' and form.validate():

        course_perm = CreateCoursePerm.query.filter_by(group_id=form.identity.data).one_or_none()
        if not course_perm:
            flash('Please choose a valid identity')
            return redirect(url_for('.add_course'))

        if not course_perm.pattern_match(form.key.data.upper()):
            flash('The course key does not match the naming rule ')
            return redirect(url_for('.add_course'))
  
        new_course = CourseRepository(key=form.key.data.upper(),
                                    name=form.name.data)
        owner_group = Group.query.filter(Group.id == form.owner_group.data).one_or_none()
        new_course.owners.append(owner_group)
        try:
            db.session.add(new_course)
            db.session.commit()
            flash('New course added.')
        except IntegrityError:
            flash('Course key already exists.')
            return redirect('/courses/')

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
    return render_template('course_create.html', form=form,group_form=group_form)


@course_bp.route('create/<course_key>/', methods=['GET', 'POST'])
@login_required
@role_permission.require(http_exception=403)
@course_manage_perm
def add_course_instance(course_key,**kwargs):

    course_repo = CourseRepository.query.filter_by(key=course_key)
    last_instance = CourseInstance.query.filter_by(course_key=course_key).first()
    if last_instance:
        form = InstanceForm(request.form, obj=CourseInstance(git_origin=last_instance.git_origin))
    else:
        form = InstanceForm(request.form)
        
    if request.method == 'POST' and form.validate():
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
@role_permission.require(http_exception=403)
@course_manage_perm
def edit_course(course_key,**kwargs): 
    course = CourseRepository.query.filter_by(key=course_key)
    course_instances = CourseInstance.query.filter_by(course_key=course_key)
    
    form = CourseEditForm(request.form, obj=course.first())
    # Get the options of identity groups
    identity_groups = Group.query.filter(Group.members.any(id=current_user.id),
                                Group.permissions.any(type=PermType.courses)).all()
    form.identity.choices += [(g.id, group_slugify(g.name,g.parent)) for g in identity_groups]    
    # The label is changes according to whether user is edit a course or creating a course,
    # When editing a course, it should be changed to follows, or it will be "First instance origin"
    form.git_origin.label = "New Git Origin for all instance"
    form.change_all.label = "Would like to change the git repo of " \
                            + str(course_instances.count()) \
                            + " instance(s) belong to this course as well?"
    if request.method == 'POST' and form.validate():
        # Check whether the course key match the naming rule
        course_perm = CreateCoursePerm.query.filter_by(group_id=form.identity.data).one_or_none()
        if not course_perm:
            flash('Please choose a valid identity group')
            return  redirect(url_for('.edit_course',course_key=course_key))
        if not course_perm.pattern_match(form.key.data.upper()):
            flash('The course key does not match the naming rule: {}'.format(course_perm.pattern))
            return  redirect(url_for('.edit_course',course_key=course_key))

        course.update(dict(
            key=form.key.data,
            name=form.name.data
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
@role_permission.require(http_exception=403)
@course_manage_perm
def edit_instance(course_key, instance_key,**kwargs):
    instance = CourseInstance.query.filter_by(key=instance_key, course_key=course_key)
    if instance is None:
        flash('There is no such instance under this course')
        return redirect('/courses/')
    else:
        form = InstanceForm(request.form, obj=instance.first())
        if request.method == 'POST' and form.validate():
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
@role_permission.require(http_exception=403)
@course_manage_perm
def del_course(course_key,**kwargs):
    if 'course' in kwargs:
        course = kwargs['course']
    else:
        course =CourseRepository.query.filter(CourseRepository.key==course_key).first()

    # The delete is cascade, the instance will be deleted as well.
    db.session.delete(course)
    db.session.commit()
    flash('Course with key: ' + course_key + ' name: ' + course.name + ' has been deleted.')
    return redirect('/courses/')


@course_bp.route('delete/<course_key>/<instance_key>/', methods=['POST'])
@login_required
@role_permission.require(http_exception=403)
@course_manage_perm
def del_course_instance(course_key, instance_key,**kwargs):
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
@role_permission.require(http_exception=403)
def instance_log(instance_id):
    instance = CourseInstance.query.filter_by(id=instance_id).first()
    if instance is None:
        flash('No such instance in the database, please refresh the page.')
        redirect('')
    render_template('instance_log.html', instance=instance)

#-------------------------------------------------------------------------------------------------#
# Ownership management

@course_bp.route('<course_key>/owners/', methods=['GET'])
@login_required
@role_permission.require(http_exception=403)
def owners_list(course_key,**kwargs):
    """Get all the owner groups of a course  
    """
    groups = db.session.query(Group).\
                    join(CourseRepository.owners).\
                    filter(CourseRepository.key==course_key).all()

    groupArray =[]

    for group in groups:
        groupObj = {'id':group.id,
                    'name':group_slugify(group.name,group.parent)}
        groupArray.append(groupObj)

    return jsonify({'owner_groups': groupArray})


@course_bp.route('<course_key>/owners/delete/', methods=['POST'])
@login_required
@role_permission.require(http_exception=403)
@course_manage_perm
def owner_remove(course_key,**kwargs):
    """Remove a owner group
    """
    course = kwargs['course']

    group_id = request.args.get('group_id')
    group = db.session.query(Group).filter_by(id=group_id).one_or_none()

    course.owners.remove(group)

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
def add_owner_list(course_key,**kwargs):

    """Get all the possible owner groups could be added for a course 
    """
    course = db.session.query(CourseRepository).\
                            join(CourseRepository.owners).\
                            filter(CourseRepository.key==course_key).\
                            filter(Group.members.any(User.id==current_user.id)).\
                            one_or_none()
    if not course:
        error_message = dumps({'message': 'Error'})
        abort(Response(error_message, 501))

    owner_groups = course.owners
    groups = [g for g in current_user.groups if g not in owner_groups]


    groupArray =[]

    for group in groups:

        groupObj = {'id':group.id,
                    'name':group_slugify(group.name,group.parent)}
        groupArray.append(groupObj)

    return jsonify({'owner_options': groupArray})


@course_bp.route('<course_key>/owners/add/', methods=['POST'])
@login_required
@role_permission.require(http_exception=403)
@course_manage_perm
def owner_add(course_key,**kwargs):
    """add a owner group
    """
    course = kwargs['course']

    group_id = request.args.get('group_id')
    group = db.session.query(Group).filter_by(id=group_id).one_or_none()

    course.owners.append(group)

    try:
        db.session.commit() 
    except:
        db.session.rollback()
        error_message = dumps({'message': 'Error occurs and could not remove the owner'})
        abort(Response(error_message, 501))

    return jsonify(status='success')



