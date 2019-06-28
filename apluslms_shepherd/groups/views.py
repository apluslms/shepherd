import logging
from json import dumps

from flask import Blueprint, render_template, url_for, redirect, request, flash, \
    Response, abort, jsonify
from flask_login import login_required, current_user

from apluslms_shepherd.auth.models import User
from apluslms_shepherd.courses.models import CourseInstance
from apluslms_shepherd.groups.forms import GroupForm
from apluslms_shepherd.groups.models import db, Group, PermType, GroupPermission, \
    CreateGroupPerm, CreateCoursePerm, CourseOwnerType, ManageCoursePerm 
from apluslms_shepherd.groups.utils import group_slugify, slugify, query_end_group, \
    role_permission, subgroup_create_perm, group_manage_perm, parent_group_check

from sqlalchemy.exc import IntegrityError
logging.basicConfig(level=logging.DEBUG)

groups_bp = Blueprint('groups', __name__, url_prefix='/groups')


# -------------------------------------------------------------------------------------------------#
# Group listing 

@groups_bp.route('/', methods=['GET'])
@login_required
@role_permission.require(http_exception=403)
def list_all_groups():
    """Listing all the groups in the database
    """
    title = "Group list"
    roots = Group.query.filter_by(parent_id=None).all()
    return render_template('groups/group_list.html', title=title, user=current_user,
                           roots=roots, node=None)


@groups_bp.route('<group_id>/subgroups/', methods=['GET'])
@login_required
@role_permission.require(http_exception=403)
def list_subgroups(group_id):
    """Listing all the subgroups of a group
    """
    group = db.session.query(Group).filter_by(id=group_id).one_or_none()
    if group is None:
        flash('There is no such group')
        return redirect(url_for('groups.list_my_groups'))

    # roots = Group.query.filter_by(parent_id=group.id).all()
    roots = group.children
    title = 'Group: ' + group_slugify(group.name, group.parent)
    return render_template('groups/group_list.html', title=title, user=current_user,
                           roots=roots, node=group)


@groups_bp.route('/my_groups/', methods=['GET'])
@login_required
@role_permission.require(http_exception=403)
def list_my_groups():
    """Listing the groups which the current user is a member of
    """
    title = "My Groups"
    groups = Group.query.join(Group.members).filter(User.id == current_user.id).all()
    group_slugs = [group_slugify(g.name, g.parent) for g in groups]
    return render_template('groups/my_groups.html', title=title, user=current_user,
                           groups=zip(groups, group_slugs), PermType=PermType)


# -------------------------------------------------------------------------------------------------#
# Group Create

def new_group_to_db(group_name, parent_group, form):
    """The function creates a new group and add it to the database
    """
    # Create a new Group instance
    if parent_group:
        new_group = Group(name=group_name, parent_id=parent_group.id)
    else:
        new_group = Group(name=group_name, parent_id=None)

    # Add the permissions to the group
    selected_perms = form.permissions.data
    for name, perm_type in PermType.__members__.items():
        if name in selected_perms:
            perm = db.session.query(GroupPermission).filter(
                GroupPermission.type == perm_type).first()
            if not perm:
                perm = GroupPermission(type=perm_type)
            new_group.permissions.append(perm)

    # If the group is a root group OR the group is permitted to manage itself
    if new_group.parent_id is None or 'self_admin' in selected_perms:
        new_group.self_admin = True
    else:
        new_group.self_admin = False

    # If the group can create courses, create CreateCoursePerm object
    if 'courses' in selected_perms:
        course_prefix = form.course_prefix.data.upper()
        course_pattern = course_prefix + '-[A-Za-z][0-9][0-9][0-9][0-9]'
        course_perm = CreateCoursePerm(group=new_group, pattern=course_pattern)
        db.session.add(course_perm)

    # Default to set the creator as a member of the group    
    new_group.members.append(current_user)
    db.session.add(new_group)

    return new_group


@groups_bp.route('create/', methods=['GET', 'POST'])
@login_required
@role_permission.require(http_exception=403)
def create_group():
    """Create a new group by giving a parent path
    """
    form = GroupForm(request.form)
    if request.method == 'POST' and form.validate():
        flash(form.data)
        # Slugify the new group name and get its parent
        group_name = slugify(form.name.data, separator='_')
        parent_group = query_end_group(form.parent_path.data)

        # Check whether the new group can be created
        if not parent_group_check(group_name, parent_group):
            return redirect(url_for('.create_group'))

        # Add the group to the database
        _ = new_group_to_db(group_name, parent_group, form)
        try:
            db.session.commit()
            flash('The new group is added, and you are set as a member of the new group')
            return redirect(url_for('.list_my_groups'))
        except:
            db.session.rollback()
            flash('Could not create the group')

    return render_template('groups/group_create.html', form=form, parent=None)


@groups_bp.route('<group_id>/create/', methods=['GET', 'POST'])
@login_required
@role_permission.require(http_exception=403)
@subgroup_create_perm
def create_subgroup(group_id, **kwargs):
    """Create a subgroup by giving the id of a parent group
    """
    if 'group' in kwargs:
        parent_group = kwargs['group']
    else:
        parent_group = db.session.query(Group).filter_by(id=group_id).one_or_none()

    form = GroupForm(request.form)

    if request.method == 'POST' and form.validate():
        # Group name should not be empty
        if form.name.data == '':
            flash('The group name can not be empty!')
            return redirect(url_for('.create_subgroup', group_id=group_id))

        group_name = slugify(form.name.data, separator='_')
        if group_name in [g.name for g in parent_group.children]:
            flash('The group already exists.')
            return redirect(url_for('.create_subgroup', group_id=group_id))

        _ = new_group_to_db(group_name, parent_group, form)
        try:
            db.session.commit()
            flash('The new group is added, and you are set as a member of the new group')
            return redirect(request.referrer)
        except:
            db.session.rollback()
            flash('Could not create the group')

    return render_template('groups/group_create.html', form=form, parent=parent_group)


@groups_bp.route('/course_group/create/', methods=['POST', 'GET'])
@login_required
def create_course_group():
    """Create a group for a course
    """
    group_id = request.args.get('group_id')

    form = GroupForm(request.form)
    if request.method == 'POST' and form.validate():
        # Check whether the group name is not empty
        if form.name.data == '':
            flash('The group name can not be empty!')
            raise Exception('The group name could not be empty')
        group_name = slugify(form.name.data, separator='_')

        # Check whether the group already exists
        parent_group = Group.query.filter_by(id=group_id).one_or_none()
        if group_name in [g.name for g in parent_group.children]:
            raise Exception('The group already exists.')

        new_group = new_group_to_db(group_name, parent_group, form)
        try:
            db.session.commit()
            flash('The new group is added,',
                  'and you are set as the admin of the new group')
        except:
            raise Exception('Could not create the group')

        return jsonify(group_id=new_group.id,
                       group_slug=group_slugify(new_group.name, new_group.parent))
    else:
        raise Exception("Error occur")


# -------------------------------------------------------------------------------------------------#
# Group management

@groups_bp.route('delete/<group_id>/', methods=['POST'])
# @groups_bp.route('delete/', methods=['POST'])
@login_required
@role_permission.require(http_exception=403)
@group_manage_perm
def delete_group(group_id, **kwargs):
    """Delete a group
    """
    group = kwargs['group']

    courses = (db.session.query(CourseInstance)
               .filter(CourseInstance.owners.any(id=group.id)).all())

    if courses:
        error_message = dumps({'message': 'You need to remove the courses to another group'})
        abort(Response(error_message, 406))

    try:
        db.session.delete(group)
        db.session.commit()
    except:
        db.session.rollback()
        logging.info('rollback')
        error_message = dumps({'message': 'Error occurs and could not remove the group'})
        abort(Response(error_message, 501))

    return jsonify(status='success')


@groups_bp.route('edit/<group_id>/', methods=['GET', 'POST'])
@login_required
@role_permission.require(http_exception=403)
@group_manage_perm
def edit_group(group_id, **kwargs):
    if 'group' in kwargs:
        group = kwargs['group']
    else:
        group = db.session.query(Group).filter_by(id=group_id).one_or_none()

    group_slug = group_slugify(group.name, group.parent)
    permissions = [perm.type.name for perm in group.permissions]
    form = GroupForm(request.form)
    form.name.label = "New group name"
    form.parent_path.label = "New parent path"
    form.permissions.label = 'Update permission'

    if request.method == 'POST' and form.validate():
        # Edit the group name
        if request.form['edit'] == 'name':
            new_name = slugify(form.name.data, separator='_')

            # Check whether the name is unchanged
            if new_name == group.name:
                flash('No changes to make for the group')
                return redirect(url_for('.edit_group', group_id=group.id))

            # Check whether there has been a group with the same name
            q = db.session.query(Group).filter_by(name=new_name,
                                                  parent_id=group.parent_id).one_or_none()
            if q:
                flash('A group with the same name has been under the same parent')
                return redirect(url_for('.edit_group', group_id=group.id))

            group.name = new_name

        # Edit the group parent    
        elif request.form['edit'] == 'parent path':

            new_parent = query_end_group(form.parent_path.data)

            if new_parent.id == group.parent_id:
                flash('No changes to make for the group')
            else:
                if parent_group_check(group.name, new_parent):
                    group.parent_id = new_parent.id

        # Edit the permissions
        elif request.form['edit'] == 'permissions':

            perm_origin = [perm.type.name for perm in group.permissions]
            perm_new = form.permissions.data

            # Manage Group.permissions field
            for name, perm_type in PermType.__members__.items():
                # The new pemission is added
                if (name not in perm_origin) and (name in perm_new):
                    perm = db.session.query(GroupPermission).filter(
                        GroupPermission.type == perm_type).first()
                    if not perm:
                        perm = GroupPermission(type=perm_type)
                    group.permissions.append(perm)

                # The original permission is removed
                if (name in perm_origin) and (name not in perm_new):
                    perm = db.session.query(GroupPermission).filter(
                        GroupPermission.type == perm_type).first()
                    group.permissions.remove(perm)

            # Set the 'self-administrator' permission
            # If it is the root, it is always self_admin
            if 'self_admin' in perm_new or group.parent is None:
                group.self_admin = True
            else:
                group.self_admin = False

            # Manage CreateCoursePerm
            # Add new CreateCoursePermission if the 'courses' permission is added
            if ('courses' not in perm_origin) and ('courses' in perm_new):
                course_prefix = form.course_prefix.data.upper()
                course_pattern = course_prefix + '-[A-Za-z][0-9][0-9][0-9][0-9]'
                course_perm = CreateCoursePerm(group=group, pattern=course_pattern)
                db.session.add(course_perm)

            # Delete the CreateCoursePermission if the 'courses' permission is removed
            if ('courses' in perm_origin) and ('courses' not in perm_new):
                create_course_perm = db.session.query(CreateGroupPerm).filter(
                    CreateGroupPerm.group_id == group.id).one_or_none()
                if create_course_perm:
                    db.session.delete(create_course_perm)

                    # Update the course prefix
        elif request.form['edit'] == 'course prefix':
            if 'courses' in permissions:
                course_prefix = form.course_prefix.data.upper()
                course_pattern = course_prefix + '-[A-Za-z][0-9][0-9][0-9][0-9]'

                create_course_perm = db.session.query(CreateCoursePerm).filter(
                    CreateCoursePerm.group_id == group.id).one_or_none()
                if create_course_perm:
                    create_course_perm.pattern = course_pattern
                else:
                    create_course_perm = CreateCoursePerm(group=group, pattern=course_pattern)
                    db.session.add(create_course_perm)
            else:
                flash('Permission Denied')

        try:
            db.session.commit()
            flash('The group is edited successfully')
            return redirect(url_for('.list_my_groups'))
        except:
            flash('The group edit failed')

    return render_template('groups/group_edit.html', group_id=group_id,
                           form=form, group_slug=group_slug, permissions=permissions)


@groups_bp.route('/<group_id>/parents/', methods=['POST', 'GET'])
@login_required
@role_permission.require(http_exception=403)
@group_manage_perm
def manage_create_group_perm(group_id, **kwargs):
    """Manage createGroupPerms UI
    """
    if 'group' in kwargs:
        group = kwargs['group']
    else:
        group = db.session.query(Group).filter_by(id=group_id).one_or_none()

    # Check whether the group has the permissions to create subgroups
    if PermType.subgroups not in [perm.type for perm in group.permissions]:
        flash('Permission Denied')
        return redirect(request.referrer)

    # The existing parent groups
    parents = db.session.query(Group). \
        join(CreateGroupPerm.target_group). \
        filter(CreateGroupPerm.group_id == group_id).all()
    parents_slug = [group_slugify(g.name, g.parent) for g in parents]

    # All the possbile parent groups are those groups the current user is a member of and their children
    possible_parents = db.session.query(Group). \
        join(Group.members). \
        filter(User.id == current_user.id).all()
    possible_parents_slug = [group_slugify(g.name, g.parent) for g in possible_parents]

    return render_template('groups/groupPerm_manage.html',
                           group_id=group_id,
                           parents=zip(parents, parents_slug),
                           possible_parents=zip(possible_parents, possible_parents_slug))


@groups_bp.route('<group_id>/parents/add/', methods=['POST'])
@login_required
@role_permission.require(http_exception=403)
@group_manage_perm
def add_create_group_perm(group_id, **kwargs):
    if 'group' in kwargs:
        group = kwargs['group']
    else:
        group = db.session.query(Group).filter_by(id=group_id).one_or_none()

    target_group_id = request.form['new_parent']

    # Check whether the permission already exists
    q = db.session.query(CreateGroupPerm). \
        filter_by(group_id=group_id, target_group_id=target_group_id).one_or_none()
    if q:
        flash('The permission has been set')
        return redirect(url_for('.manage_create_group_perm', group_id=group.id))

    target_group = db.session.query(Group).filter_by(id=target_group_id).one_or_none()
    group_perm = CreateGroupPerm(group=group, target_group=target_group)

    try:
        db.session.add(group_perm)
        db.session.commit()
        flash('The new permission is set')
    # except IntegrityError:
    #     db.session.rollback()
    #     flash('The permission already exists')
    except:
        db.session.rollback()
        flash('Could not add the permission')

    return redirect(url_for('.manage_create_group_perm', group_id=group_id))


@groups_bp.route('<group_id>/parents/remove/', methods=['POST'])
@login_required
@role_permission.require(http_exception=403)
@group_manage_perm
def del_create_group_perm(group_id, **kwargs):
    if 'group' in kwargs:
        group = kwargs['group']
    else:
        group = db.session.query(Group).filter_by(id=group_id).one_or_none()

    target_group_id = request.form['del_parent']
    # Check whether the permission exists
    flash(group.id, target_group_id)
    group_perm = db.session.query(CreateGroupPerm). \
        filter_by(group_id=group_id, target_group_id=target_group_id).one_or_none()
    if not group_perm:
        flash('No such a permission')
        return redirect(url_for('.manage_create_group_perm', group_id=group.id))

    try:
        db.session.delete(group_perm)
        db.session.commit()
        flash('The permission is removed')
    except:
        db.session.rollback()
        flash('Could not remove the permission')

    return redirect(url_for('.manage_create_group_perm', group_id=group_id))


# -------------------------------------------------------------------------------------------------#
# Group membership management

@groups_bp.route('<group_id>/members/', methods=['GET'])
@login_required
@role_permission.require(http_exception=403)
def list_members(group_id):
    """Listing the members of a group
    """
    title = "Member list"
    group = Group.query.filter_by(id=group_id).one_or_none()

    if group is None:
        flash('There is no such group')
        return redirect(request.referrer)

    members = group.members

    # Check the permission to manage membership
    allow_manage = False
    if group.self_admin and current_user in group.members:
        allow_manage = True
    else:
        ancestors = group.path_to_root().all()
        for ancestor in ancestors[1:]:
            if current_user in ancestor.members:
                allow_manage = True
                break

    return render_template('members/member_list.html', title=title, user=current_user,
                           group=group, members=members, allow_manage=allow_manage)


@groups_bp.route('/<group_id>/add_members/', methods=['GET'])
@login_required
@role_permission.require(http_exception=403)
def list_users(group_id):
    """Listing the possible users who can be added as the members of a group
    """
    group = db.session.query(Group).filter_by(id=group_id).one_or_none()

    # The possible users are those with role permission and not are the members of the group
    conditions = []
    for role in ['Instructor', 'Mentor', 'Teacher', 'TeachingAssistant', 'TA']:
        conditions.append(User.roles.contains(role))

    available_users = db.session.query(User).filter(db.or_(*conditions),
                                                    db.not_(User.groups.any(Group.id == group.id))).all()

    return render_template('members/members_add.html', group=group, users=available_users)


@groups_bp.route('<group_id>/members/add/', methods=['POST'])
@login_required
@role_permission.require(http_exception=403)
@group_manage_perm
def add_member(group_id, **kwargs):
    """Add a member to a group
    """
    if 'group' in kwargs:
        group = kwargs['group']
    else:
        group = db.session.query(Group).filter_by(id=group_id).one_or_none()

    user_id = request.form['user']
    # Query the user by id and roles
    conditions = []
    for role in ['Instructor', 'Mentor', 'Teacher', 'TeachingAssistant', 'TA']:
        conditions.append(User.roles.contains(role))

    new_member = db.session.query(User).filter(User.id == user_id,
                                               db.or_(*conditions), ).one_or_none()
    if new_member is None:
        flash('No such a user')
        return redirect(url_for('.list_users', group_id=group.id))

    group.members.append(new_member)

    try:
        db.session.commit()
        flash('The new member is added')
    except:
        db.session.rollback()
        flash('Could not add this user')

    return redirect(url_for('.list_users', group_id=group.id))


@groups_bp.route('/<group_id>/members/delete/', methods=['POST'])
@login_required
@role_permission.require(http_exception=403)
@group_manage_perm
def delete_member(group_id, **kwargs):
    """Remove a member from a group
    """
    if 'group' in kwargs:
        group = kwargs['group']
    else:
        group = db.session.query(Group).filter_by(id=group_id).one_or_none()

    user_id = request.form['user']
    member = db.session.query(User).filter_by(id=user_id).one_or_none()
    if member is None:
        flash('No such a user')
        return redirect(url_for('.list_members', group_id=group.id))
    
    # If the group is the root and the user is the only member, 
    # it could not be removed
    if (not group.parent) and (len(group.members)==1):
        flash('The only member of the root group could not be removed')
        return redirect(url_for('.list_members', group_id=group.id))

    group.members.remove(member)

    try:
        db.session.commit()
        flash('The member is removed')
    except:
        db.session.rollback()
        flash('Could not remove this user')

    return redirect(url_for('.list_members', group_id=group.id))


@groups_bp.route('/move_course/', methods=['POST', 'GET'])
@login_required
@role_permission.require(http_exception=403)
@group_manage_perm
def move_course(**kwargs):
    """Move courses of a group to another group
    """
    old_owner = kwargs['group']

    new_owner_id = request.args.get('new_owner_id')
    new_owner = (db.session.query(Group)
                        .filter_by(id=new_owner_id).one_or_none())

    course_instances = (db.session.query(CourseInstance)
                        .join(CourseInstance.owners)
                        .filter(Group.id == old_owner.id).all())

    for c in course_instances:
            c.owners.remove(old_owner)
            if new_owner not in c.owners:
                c.owners.append(new_owner)

    course_manage_perms = (db.session.query(ManageCoursePerm)
                        .filter(ManageCoursePerm.group_id == old_owner.id))
    course_instance_ids = [p.course_instance_id for p in course_manage_perms]

    q = (db.session.query(ManageCoursePerm)
                        .filter(ManageCoursePerm.course_instance_id.in_(course_instance_ids))
                        .filter(ManageCoursePerm.group_id == new_owner_id))
    if not q.all():
        course_manage_perms.update({'group_id':new_owner_id})
    else:
        q_course_instances = {p.course_instance_id: p for p in q}
        for perm in course_manage_perms.all():
            if perm.course_instance_id in q_course_instances:
                new_perm = q_course_instances[perm.course_instance_id]
                if not new_perm.type == CourseOwnerType.admin:
                    if perm.type == CourseOwnerType.admin:
                        new_perm.type = CourseOwnerType.admin
                    
                db.session.delete(perm)
            else:
                perm.group = new_owner
    try:
        db.session.commit()
    except:
        db.session.rollback()
        raise Exception('Could not change the owner of the courses')

    return jsonify(status="success")


# -------------------------------------------------------------------------------------------------#
# Helper views

@groups_bp.route('perm/<group_id>/parents/', methods=['GET'])
@login_required
@role_permission.require(http_exception=403)
def parent_options(group_id):
    """Get all the possible parent groups of subgroups 
    for a group has the create subgroup permission  
    """
    groups = (db.session.query(Group)
              .join(CreateGroupPerm.target_group)
              .filter(CreateGroupPerm.group_id == group_id).all())

    group_array = []

    for group in groups:
        group_obj = {'id': group.id,
                     'name': group_slugify(group.name, group.parent)}
        group_array.append(group_obj)

    return jsonify({'parent_options': group_array})


@groups_bp.route('/options_of_new_owner/', methods=['GET'])
@login_required
@role_permission.require(http_exception=403)
def owner_options():
    """Get all the possible new owner groups for a course 
    """
    old_owner_id = request.args.get('old_owner_id')
    old_owner = Group.query.filter_by(id=old_owner_id).one_or_none()

    if not old_owner:
        abort(404, 'No such a group')

    groups = current_user.groups
    groups.remove(old_owner)  # Remove the original owner group from the options

    # OR:
    # group_table =Group.__table__
    # old_owner = db.session.query(group_table).filter(
    #             group_table.c.id==old_owner_id).one_or_none()
    # groups = db.session.query(Group,group_table).\
    #         join(Group.members).\
    #         filter(Group.members.any(User.id==current_user.id)).\
    #         filter(db.or_(group_table.c.tree_id != old_owner.tree_id,
    #                     db.and_(
    #                     group_table.c.tree_id == old_owner.tree_id,
    #                     group_table.c.lft<old_owner.lft,
    #                     group_table.c.rgt>old_owner.rgt))).all()

    group_array = []

    for group in groups:
        # the group could not be the descendant of the original owner group
        if not group.is_descendant_of(old_owner):
            group_obj = {'id': group.id,
                         'name': group_slugify(group.name, group.parent)}
            group_array.append(group_obj)

    return jsonify({'owner_options': group_array})
