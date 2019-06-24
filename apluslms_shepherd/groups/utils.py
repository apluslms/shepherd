from flask import request, flash, redirect, url_for, abort, Response
from flask_login import current_user
from flask_principal import Permission, RoleNeed

from apluslms_shepherd.extensions import db
from apluslms_shepherd.auth.models import User
from apluslms_shepherd.groups.models import Group, PermType, CreateGroupPerm, CreateCoursePerm
from apluslms_shepherd.courses.models import CourseInstance
from collections import namedtuple
from functools import partial
from functools import wraps
from slugify import slugify
from json import dumps

import logging

logging.basicConfig(level=logging.DEBUG)

# -------------------------------------------------------------------------------------------------#
# Permission objects

# Permission types (dict)
PERM_TYPE = {'self_admin': 'self-administrator',
             'subgroups': 'create subgroups', 'courses': 'create courses'}
# The list of permission tuples (for forms)            
PERMISSION_LIST = list(perm_tuple for perm_tuple in PERM_TYPE.items())

# Create the permission with RoleNeeds.
role_permission = Permission(RoleNeed('Instructor'), RoleNeed('Mentor'),
                             RoleNeed('Teacher'), RoleNeed('TA'), RoleNeed('TeachingAssistant'))


# -------------------------------------------------------------------------------------------------#
# Decorators for permission checking

def subgroup_create_perm(func):
    """
    Check whether the current user can create a subgroup under a group.
    Permission: 1.the user is a member of the ancestors of the group
                OR
                2. the group is the target group where subgroups can be created under.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        allowed = False  # Init allowed flag

        if "group_id" in request.view_args:
            group_id = request.view_args['group_id']
            group = db.session.query(Group).filter_by(id=group_id).one_or_none()

            # Check condition 1
            ancestors = group.path_to_root().all()
            for ancestor in ancestors[1:]:
                if current_user in ancestor.members:
                    allowed = True
                    kwargs['group'] = group
                    break

            # If condition 1 doesn't meet, check condition 2
            if not allowed:
                perms = db.session.query(CreateGroupPerm). \
                    join(CreateGroupPerm.group). \
                    filter(CreateGroupPerm.target_group_id == group_id). \
                    filter(Group.members.any(User.id == current_user.id)).all()
                if perms:
                    allowed = True
                    kwargs['group'] = group

        if not allowed:
            flash('Permission denied')
            return redirect(request.referrer)

        return func(*args, **kwargs)

    return wrapper


def group_manage_perm(func):
    """
    Check whether the current user can manage a group (edit, delete, manage membership)
    Permission: 1. the user is a member of the group with the permission to self-admin
                OR
                2. the user is a member of one of its ancestor groups 
    """

    @wraps(func)
    def wrapper(*args, **kwargs):

        allowed = False  # Init flag

        # Get the group
        if "group_id" in request.view_args:
            group_id = request.view_args['group_id']
            group = db.session.query(Group).filter_by(id=group_id).one_or_none()
        elif "group_id" in request.args:
            group_id = request.args.get('group_id')
            group = db.session.query(Group).filter_by(id=group_id).one_or_none()
        elif "old_owner_id" in request.args:
            group_id = request.args.get('old_owner_id')
            group = db.session.query(Group).filter_by(id=group_id).one_or_none()
        else:
            flash('Could not get the group info')
            return redirect(url_for('groups.list_my_groups'))

        if group:
            # Check condtion 1 
            if group.self_admin and current_user in group.members:
                allowed = True
                kwargs['group'] = group
            else:  # Check condition 2
                ancestors = group.path_to_root().all()
                for ancestor in ancestors[1:]:
                    if current_user in ancestor.members:
                        allowed = True
                        kwargs['group'] = group
                        break

        if not allowed:
            if 'return_error' in request.args:
                logging.info('return_error')
                error_message = dumps({'message': 'Permssion Denied'})
                abort(Response(error_message, 403))
            else:
                flash('Permission denied')
                return redirect(url_for('groups.list_my_groups'))

        return func(*args, **kwargs)

    return wrapper


def course_create_perm(func):
    """
    Check whether the current user can create a course
    Permission: the user is a member of a group with the permission to create courses
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        # Check whether any of the groups that current user is in has the permission
        # group_IDs = [g.id for g in current_user.groups] 
        # allowed = db.session.query(CreateCoursePerm).filter(CreateCoursePerm.group_id.in_(group_IDs)).all()
        identity_groups = Group.query.filter(Group.members.any(id=current_user.id),
                                             Group.permissions.any(type=PermType.courses)).all()
        if not identity_groups:
            flash('Permission denied')
            return redirect(request.referrer)

        kwargs['identity_groups'] = identity_groups
        return func(*args, **kwargs)

    return wrapper


def course_manage_perm(func):
    """
    Check whether the current user can manage a course
    Permission: the user is a member of the owner groups of the course
    """

    @wraps(func)
    def wrapper(*args, **kwargs):

        if "course_key" in request.view_args:
            course_key = request.view_args['course_key']
            course = db.session.query(CourseInstance). \
                join(CourseInstance.owners). \
                filter(CourseInstance.course_key == course_key). \
                filter(Group.members.any(User.id == current_user.id)).one_or_none()

        if not course:
            if 'return_error' in request.args:
                error_message = dumps({'message': 'Permssion Denied'})
                abort(Response(error_message, 403))
            else:
                flash('Permission denied')
                return redirect('/courses/')

        kwargs['course'] = course
        return func(*args, **kwargs)

    return wrapper


# Function for permission checking

def parent_group_check(group_name, parent_group):
    """
    Check whether the group with group_name can be create under the parent group
    """
    # Group name should not be empty
    if group_name == '':
        flash('The group name can not be empty!')
        return None

    # Check whether there exists such a parent group
    if parent_group == -1:
        flash('No such a parent path')
        return None

    # Check whether the parent group already has a child with the same group name
    if not parent_group:  # The new group is a root 
        g = db.session.query(Group).filter_by(name=group_name,
                                              parent=parent_group).one_or_none()
        if g:
            flash('The group already exists.')
            return None
        return True
    else:
        if group_name in [g.name for g in parent_group.children]:
            flash('The group already exists.')
            return None

    # Check the permission
    # Check whether the user is a member of the ancestors of the parent group
    ancestors = parent_group.path_to_root().all()
    for ancestor in ancestors[1:]:
        if current_user in ancestor.members:
            return parent_group

    # Check whether the parent group is the target group where subgroups can be created under.
    perms = db.session.query(CreateGroupPerm). \
        join(CreateGroupPerm.group). \
        filter(CreateGroupPerm.target_group_id == parent_group.id). \
        filter(Group.members.any(User.id == current_user.id)).all()
    if perms:
        return parent_group

    return None


# -------------------------------------------------------------------------------------------------#

def group_slugify(group_name, parent, separator='.'):
    """
    Generate the slug of a group.
    :param group_name (str): name of the group
    :param parent (Group instance): parent group
    :param separator (str): separator between words
    :return (str): the group slug
    """
    regex_pattern = r'[^-a-z0-9_]+'

    if parent is None:  # If the group is the root
        return slugify(group_name, separator=separator, regex_pattern=regex_pattern)
    else:
        # Else, first find the path from the root to its parent  
        path_name = [n.name for n in parent.path_to_root().all()][::-1]
        # add the group to the end of the list 
        path_name.append(group_name)
        return slugify(' '.join(path_name), separator=separator, regex_pattern=regex_pattern)


def query_end_group(group_path):
    """
    Get the end group in a group path.
    :param group_path (str): a string representing a path from 
                            the root to a ancestor, e.g., 'aalto.sci.cs'
    :return (Group instance): 
    """
    end_group = None  # Init, the parent_id of the root

    if group_path == '':  # If the path is null, the new group is the root
        return end_group

    # Get the list of groups
    group_list = group_path.lower().split('.')
    # Query from the root to the end
    for group_name in group_list:
        q = Group.query.filter_by(name=group_name, parent=end_group).one_or_none()
        if q:
            end_group = q  # Update the group
        else:  # The group does not exist in the database (no such group path)
            return -1

    return end_group

# -------------------------------------------------------------------------------------------------#
