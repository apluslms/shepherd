from collections import namedtuple
from functools import partial
from functools import wraps

from flask import request, flash, redirect
from flask_principal import Permission, RoleNeed
from slugify import slugify
from flask_login import current_user
from apluslms_shepherd.extensions import db
from apluslms_shepherd.groups.models import Group,PermType,CreateCoursePerm


def group_slugify(group_name, parent_id, separator='.'):
    regex_pattern = r'[^-a-z0-9_]+'
    if parent_id is None:
        return slugify(group_name, separator=separator, regex_pattern=regex_pattern)
    else:
        parent = Group.query.filter_by(id=parent_id).one_or_none()
        parent_path = parent.path_to_root().all()
        path_name = [n.name for n in parent_path][::-1]
        path_name.append(group_name)
        return slugify(' '.join(path_name), separator=separator, regex_pattern=regex_pattern)


def query_parent_id(group_path):
    parent_id = None
    if group_path == '':
        return parent_id

    group_path = group_path.lower()
    group_list = group_path.split('.')
    for group in group_list:
        q = Group.query.filter_by(name=group, parent_id=parent_id).one_or_none()
        if q:
            parent_id = q.id
        else:
            return -1
    return parent_id


# Create the permission with RoleNeeds.
role_permission = Permission(RoleNeed('Instructor'), RoleNeed('Mentor'),
                             RoleNeed('Teacher'), RoleNeed('TA'), RoleNeed('TeachingAssistant'))

GroupNeed = namedtuple('GroupNeed', ['action', 'group_id'])
CourseNeed = namedtuple('CourseNeed', ['action', 'group_id'])
MemberNeed = namedtuple('MembershipNeed', ['action', 'group_id'])

SubgroupNeed = partial(GroupNeed, 'manage')
SelfAdminNeed = partial(GroupNeed, 'self-admin')
CourseManageNeed = partial(CourseNeed, 'manage')
MemberManageNeed = partial(MemberNeed, 'manage')


class SubgroupPermission(Permission):
    """Extend Permission to take a group_id and action as arguments"""

    def __init__(self, group_id):
        need = SubgroupNeed(str(group_id))
        super(SubgroupPermission, self).__init__(need)


class SelfAdminPermission(Permission):
    """Extend Permission to take a group_id and action as arguments"""

    def __init__(self, group_id):
        need = SelfAdminNeed(str(group_id))
        super(SelfAdminPermission, self).__init__(need)


class CourseManagePermission(Permission):
    def __init__(self, group_id):
        need = CourseManageNeed(str(group_id))
        super(CourseManagePermission, self).__init__(need)


class MemberManagePermission(Permission):
    def __init__(self, group_id):
        need = MemberManageNeed(str(group_id))
        super(MemberManagePermission, self).__init__(need)


def group_create_perm(func):
    @wraps(func)
    def wrapper(*args, **kwargs):

        allowed = False
        if "group_id" in request.view_args:
            group_id = request.view_args['group_id']
            group = db.session.query(Group).filter_by(id=group_id).one_or_none()

            ancestors = group.path_to_root().all()
            for ancestor in ancestors:
                permission = SubgroupPermission(group_id=ancestor.id)
                if permission.can():
                    allowed = True
                    break

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
            group = db.session.query(Group).filter_by(id=group_id).one_or_none()

            permission = SelfAdminPermission(group_id=group_id)
            if permission.can():
                allowed = True
            else:
                ancestors = group.path_to_root().all()
                for ancestor in ancestors:
                    permission = SubgroupPermission(group_id=ancestor.id)
                    if permission.can():
                        allowed = True
                        break

        if not allowed:
            flash('Permission denied')
            return redirect(request.referrer)

        return func(*args, **kwargs)

    return wrapper

def membership_perm(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        allowed = False

        if "group_id" in request.view_args:
            group_id = request.view_args['group_id']
            group = db.session.query(Group).filter_by(id=group_id).one_or_none()

            permission = SelfAdminPermission(group_id=group_id)
            if permission.can():
                allowed = True
            else:
                ancestors = group.path_to_root().all()
                for ancestor in ancestors:
                    permission =MemberManagePermission(group_id=ancestor.id)
                    if permission.can():
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
        groups = current_user.groups
        # perm = db.session.query(CreateCoursePerm).filter(Group.id == group_id).one_or_none()
        for group in groups:
            # if PermType.courses in [ perm.type for perm in group.permissions]:
            if db.session.query(CreateCoursePerm).filter(CreateCoursePerm.group_id == group.id).one_or_none():
                allowed = True
                break

        if not allowed:
            flash('Permission denied')
            return redirect(request.referrer)

        return func(*args, **kwargs)

    return wrapper

# ------------------------------------------------------------------------------------------------------------#
# def group_create_perm(func):

#     @wraps(func)
#     def wrapper(*args, **kwargs):
#         allowed = False
#         if "group_id" in request.view_args:
#             group_id = request.view_args['group_id']
#             group = db.session.query(Group).filter(Group.id==group_id,
#                                             Group.permissions.any(GroupPermission.type==PermType.groups),
#                                             Group.members.any(User.id==current_user.id)).one_or_none()
#             if group:
#                 allowed = True
#         if not allowed:
#             flash('Permission denied')
#             return redirect(request.referrer)
#         return func(*args, **kwargs)
#     return wrapper


# def group_edit_del_perm(func):

#     @wraps(func)
#     def wrapper(*args, **kwargs):
#         allowed = False
#         if "group_id" in request.view_args:
#             group_id = request.view_args['group_id']
#             group = db.session.query(Group).filter(Group.id==group_id).one_or_none()
#             if group:
#                 parent_group = db.session.query(Group).filter(Group.id==group.parent_id,
#                                             Group.members.any(User.id==current_user.id)).one_or_none()
#                 if parent_group:
#                     for perm in parent_group.permissions:
#                         if perm.type == PermType.groups:
#                             allowed = True
#                             break
#         if not allowed:
#             flash('Permission denied')
#             return redirect(request.referrer)
#         return func(*args, **kwargs)
#     return wrapper


# def course_perm(func):

#     @wraps(func)
#     def wrapper(*args, **kwargs):
#         allowed = False
#         if "group_id" in request.view_args:
#             group_id = request.view_args['group_id']
#             group = db.session.query(Group).filter(Group.id==group_id,
#                                             Group.members.any(User.id==current_user.id)).one_or_none()
#             if group:
#                 for perm in group.permissions:
#                     if perm.type == PermType.groups:
#                         allowed = True
#                         break
#         if not allowed:
#             flash('Permission denied')
#             return redirect(request.referrer)
#         return func(*args, **kwargs)
#     return wrapper
