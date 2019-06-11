from flask import request, flash, redirect, url_for
from flask_login import current_user
from flask_principal import Permission, RoleNeed

from apluslms_shepherd.extensions import db
from apluslms_shepherd.groups.models import Group, PermType, CreateGroupPerm, CreateCoursePerm

from collections import namedtuple
from functools import partial
from functools import wraps
from slugify import slugify

#-------------------------------------------------------------------------------------------------#
def group_slugify(group_name, parent_id, separator='.'):
    """
    Generate the slug of a group.
    :param group_name (str): name of the group
    :param parent_id (int): id of the group's parent
    :param separator (str): separator between words
    :return (str): the group slug
    """
    regex_pattern = r'[^-a-z0-9_]+'

    if parent_id is None: # If the group is the root
        return slugify(group_name, separator=separator, regex_pattern=regex_pattern)
    else: 
        # Else, first find the path from the root to its parent  
        parent = Group.query.filter_by(id=parent_id).one_or_none()
        parent_path = parent.path_to_root().all()
        path_name = [n.name for n in parent_path][::-1]
        # add the group to the end of the list 
        path_name.append(group_name)
        return slugify(' '.join(path_name), separator=separator, regex_pattern=regex_pattern)


def query_end_group_id(group_path):
    """
    Get the id of the end group in a group path.
    :param group_path (str): a string representing a path from 
                            the root to a ancestor, e.g., 'aalto.sci.cs'
    :return (int): the id of the last group, e.g., id of 'cs' in the path 'aalto.sci.cs'
    """
    end_group_id = None  # Init, the parent_id of the root

    if group_path == '':  # If the path is null, return 
        return end_group_id
        
    # Get the list of groups
    group_list = group_path.lower().split('.')  
    # Query from the root to the end
    for group in group_list:
        q = Group.query.filter_by(name=group, parent_id=end_group_id).one_or_none()
        if q:
            end_group_id = q.id # Update the id
        else:  # The group does not exist in the database (no such group path)
            return -1

    return end_group_id

#-------------------------------------------------------------------------------------------------#

# Permission types (dict)
PERM_TYPE = {'self_admin':'self-administrator',
            'subgroups': 'create subgroups','courses': 'create courses'}
# The list of permission tuples (for forms)            
PERMISSION_LIST = list(perm_tuple for perm_tuple in PERM_TYPE.items())

# Create the permission with RoleNeeds.
role_permission = Permission(RoleNeed('Instructor'), RoleNeed('Mentor'),
                             RoleNeed('Teacher'), RoleNeed('TA'), RoleNeed('TeachingAssistant'))

# Create Need and Permission objects
GroupNeed = namedtuple('GroupNeed', ['action', 'group_id'])
CourseNeed = namedtuple('CourseNeed', ['action', 'group_id'])

SelfAdminNeed = partial(GroupNeed, 'self_admin')
SubgroupCreateNeed = partial(GroupNeed, 'create')
CourseCreateNeed = partial(CourseNeed, 'create')


class SelfAdminPermission(Permission):
    def __init__(self, group_id):
        need = SelfAdminNeed(str(group_id))
        super(SelfAdminPermission, self).__init__(need)


class SubgroupCreatePermission(Permission):
    def __init__(self, group_id):
        need = SubgroupCreateNeed(str(group_id))
        super(SubgroupCreatePermission, self).__init__(need)


class CourseCreatePermission(Permission):
    def __init__(self, group_id):
        need = CourseCreateNeed(str(group_id))
        super(CourseCreatePermission, self).__init__(need)

#-------------------------------------------------------------------------------------------------#
# Decorators for permission checking

def subgroup_create_perm(func):
    """
    Check whether the current user can create a subgroup under a group.
    Permission: 1. the user is a member of the group with the permission to self-admin
                OR
                2. the group is the target group where subgroups can be created under.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        allowed = False # Init allowed flag

        if "group_id" in request.view_args:
            group_id = request.view_args['group_id'] 
            
            permission = SelfAdminPermission(group_id=group_id)
            if permission.can():  # the group is self-admin and the current user is its member
            # if current_user in group.members:
                allowed = True
            else:
                # Check whether the group is a target_group permitted to create subgroups
                groups = db.session.query(CreateGroupPerm).filter_by(target_group_id=group_id).all()
                if groups:
                    for g in groups: 
                        if current_user in g.members:
                            allowed = True
                            break

        if not allowed:
            flash('Permission denied')
            return redirect(url_for('groups.list_my_groups'))

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

        allowed = False

        if "group_id" in request.view_args:
            group_id = request.view_args['group_id']
            group = db.session.query(Group).filter_by(id=group_id).one_or_none()
        
            permission = SelfAdminPermission(group_id=group_id)
            if permission.can():  # the group is self-admin and the current user is its member
            # if current_user in group.members:
                allowed = True
            else:
                ancestors = group.path_to_root().all()
                # Check whether the current user is in any of its ancestor groups
                for ancestor in ancestors:
                    if current_user in ancestor:
                        allowed = True
                        break

        if not allowed:
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

        group_IDs = [g.id for g in current_user.groups] 
        # Check whether any of the groups that current user is in has the permission
        allowed = db.session.query(CreateCoursePerm).filter(CreateCoursePerm.group_id.in_(group_IDs)).all()
        if not allowed:
            flash('Permission denied')
            return redirect('/')

        return func(*args, **kwargs)

    return wrapper
#-------------------------------------------------------------------------------------------------#
