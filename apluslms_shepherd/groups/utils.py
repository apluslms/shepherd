from slugify import slugify
from flask import request,flash,redirect
from flask_login import current_user
from apluslms_shepherd.extensions import db
from apluslms_shepherd.groups.models import Group,GroupPermission,PermType
from apluslms_shepherd.auth.models import User
from flask_principal import Principal, Identity, AnonymousIdentity, \
    identity_changed, identity_loaded, RoleNeed, UserNeed,Permission, RoleNeed
from functools import wraps
from collections import namedtuple
from functools import partial   


def group_slugify(group_name,parent_id,separator='.'):
    regex_pattern = r'[^-a-z0-9_]+'
    if parent_id is None:
        return slugify(group_name,separator=separator,regex_pattern=regex_pattern)
    else:    
        parent = Group.query.filter_by(id=parent_id).one_or_none()
        parent_path = parent.path_to_root().all()
        path_name = [n.name for n in parent_path][::-1]
        path_name.append(group_name)
        return slugify(' '.join(path_name),separator=separator,regex_pattern=regex_pattern)


def query_parent_id(group_path):
    group_path = group_path.lower()
    parent_id = None
    if group_path == '':
        return -1

    group_path = group_path.lower()
    group_list = group_path.split('.')
    for group in group_list:
        q = Group.query.filter_by(name=group,parent_id=parent_id).one_or_none()
        if q:
            parent_id = q.id
        else:
            return -1
    return parent_id


# Create the permission with RoleNeeds.
role_permission = Permission(RoleNeed('Instructor'),RoleNeed('Mentor'),
                RoleNeed('Teacher'),RoleNeed('TA'),RoleNeed('TeachingAssistant'))

GroupNeed = namedtuple('GroupNeed', ['action', 'group_id'])
CourseNeed = namedtuple('CourseNeed', ['action', 'group_id'])

CreateGroupNeed = partial(GroupNeed, 'create')
CreateCourseNeed = partial(CourseNeed, 'create')


class CreateGroupPermission(Permission):
    """Extend Permission to take a group_id and action as arguments"""
    def __init__(self, action, group_id=None):
        need = CreateGroupNeed(action, group_id)
        super(CreateGroupPermission, self).__init__(need)

class CreateCoursePermission(Permission):
    def __init__(self, group_id):
        need = CreateCourseNeed(group_id)
        super(CreateCoursePermission, self).__init__(need)


def group_create_perm(func):

    @wraps(func)
    def wrapper(*args, **kwargs):
        allowed = False
        if "group_id" in request.view_args:
            group_id = request.view_args['group_id']
            group = db.session.query(Group).filter(Group.id==group_id,
                                            Group.permissions.any(GroupPermission.type==PermType.groups),
                                            Group.members.any(User.id==current_user.id)).one_or_none()
            if group:
                allowed = True
        if not allowed:
            flash('Permission denied')
            return redirect(request.referrer)
        return func(*args, **kwargs)
    return wrapper


def group_edit_del_perm(func):

    @wraps(func)
    def wrapper(*args, **kwargs):
        allowed = False
        if "group_id" in request.view_args:
            group_id = request.view_args['group_id']
            group = db.session.query(Group).filter(Group.id==group_id).one_or_none()
            if group:
                parent_group = group = db.session.query(Group).filter(Group.id==group.parent_id,
                                            Group.members.any(User.id==current_user.id)).one_or_none()
                if parent_group:
                    for perm in parent_group.permissions:
                        if perm.type == PermType.groups:
                            allowed = True
                            break
        if not allowed:
            flash('Permission denied')
            return redirect(request.referrer)
        return func(*args, **kwargs)
    return wrapper


def course_perm(func):

    @wraps(func)
    def wrapper(*args, **kwargs):
        allowed = False
        if "group_id" in request.view_args:
            group_id = request.view_args['group_id']
            group = db.session.query(Group).filter(Group.id==group_id,
                                            Group.members.any(User.id==current_user.id)).one_or_none()
            if group:
                for perm in group.permissions:
                    if perm.type == PermType.groups:
                        allowed = True
                        break
        if not allowed:
            flash('Permission denied')
            return redirect(request.referrer)
        return func(*args, **kwargs)
    return wrapper

