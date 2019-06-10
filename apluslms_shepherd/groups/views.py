import logging

from flask import Blueprint, render_template, url_for
from flask_login import login_required, current_user

from apluslms_shepherd.auth.models import User
from apluslms_shepherd.groups.forms import GroupForm
from apluslms_shepherd.groups.models import GroupPermission, PermType,CreateGroupPerm,CreateCoursePerm,PERMISSION_LIST
from apluslms_shepherd.groups.utils import *
import json
from flask import jsonify
logging.basicConfig(level=logging.DEBUG)

groups_bp = Blueprint('groups', __name__, url_prefix='/groups')


@groups_bp.route('/', methods=['GET'])
@login_required
@role_permission.require(http_exception=403)
def list_all_groups():
    title = "Group list"
    roots = Group.query.filter_by(parent_id=None).all()
    return render_template('groups/group_list.html', title=title, user=current_user, roots=roots, group=None)


@groups_bp.route('<group_id>/subgroups/', methods=['GET'])
@login_required
@role_permission.require(http_exception=403)
def list_subgroups(group_id):
    group = db.session.query(Group).filter_by(id=group_id).one_or_none()
    if group is None:
        flash('There is no such group')
        return redirect(request.referrer)
    else:
        title = 'Group: ' + group_slugify(group.name, group.parent_id)
        roots = Group.query.filter_by(parent_id=group.id).all()
    return render_template('groups/group_list.html', title=title, user=current_user, roots=roots, group=group)


@groups_bp.route('/my_groups/', methods=['GET'])
@login_required
@role_permission.require(http_exception=403)
def list_my_groups():
    title = "My Groups"
    groups = Group.query.join(Group.members).filter(User.id == current_user.id).all()
    group_slugs = [group_slugify(g.name, g.parent_id) for g in groups]
    return render_template('groups/my_groups.html', title=title, user=current_user, groups=zip(groups, group_slugs),
                           PermType=PermType)


@groups_bp.route('create/', methods=['GET', 'POST'])
@login_required
@role_permission.require(http_exception=403)
def create_group():
    
    flash(request.path)
       
    form = GroupForm(request.form)
    parents_of_subgroups = db.session.query(Group).filter(
                            Group.permissions.any(type=PermType.groups)).all()
    form.target_groups.choices += ([(g.id, group_slugify(g.name,g.parent_id)) for g in parents_of_subgroups])

    if request.method == 'POST' and form.validate():
        group_name = slugify(form.name.data, separator='_')
        parent_id = query_parent_id(form.parent_path.data)

        if parent_id == -1:
            flash('No such a parent path ' + form.parent_path.data)
            return redirect(url_for('.create_group'))

        parent = Group.query.filter_by(id=parent_id).one_or_none()
        if parent and current_user not in parent.members:
            flash('You are not the member of this group, could not create subgroups')
            return redirect(url_for('.create_group'))

        q = Group.query.filter_by(name=group_name, parent_id=parent_id).one_or_none()
        if q is not None:
            flash('The group ' + group_slugify(group_name, parent_id) + ' already exists.')
            return redirect(url_for('.create_group'))
        
        new_group = Group(name=group_name, parent_id=parent_id)
        perm_selected = form.permissions.data

        for name, perm_type in PermType.__members__.items():
            if name in perm_selected:
                perm = db.session.query(GroupPermission).filter(
                    GroupPermission.type == perm_type).first()
                if not perm:
                    perm = GroupPermission(type=perm_type)
                    db.session.add(perm)
                    db.session.commit()
                new_group.permissions.append(perm)

        course_perm,group_perms = None, None
        if new_group.parent_id is None or 'self_admin' in perm_selected:
            new_group.self_admin = True
        else:
            new_group.self_admin = False
        
        if 'courses' in perm_selected:
            course_prefix = form.course_prefix.data.upper()
            course_pattern = course_prefix + '-[A-Za-z][0-9][0-9][0-9][0-9]'
            course_perm = CreateCoursePerm(group=new_group,pattern=course_pattern)
        
        if 'groups' in perm_selected:
            parent_group_ids = form.target_groups.data
            if len(parent_group_ids) == 0:
                flash('You must choose a parent group')
                return redirect(url_for('.create_group'))
            group_perms = []
            for g_id in parent_group_ids:
                if g_id==0:
                    group_perm = CreateGroupPerm(group=new_group,target_group=new_group)
                else:
                    target_group = db.session.query(Group).filter_by(id=g_id).one_or_none()
                    group_perm = CreateGroupPerm(group=new_group,target_group=target_group)
                    # group_perm = CreateGroupPerm(group=new_group,target_group_id=g_id)
                group_perms.append(group_perm)
        try:
            flash(form.data)
            new_group.members.append(current_user)
            db.session.add(new_group)
            if course_perm: 
                db.session.add(course_perm)
            if group_perms:
                for group_perm in group_perms:
                    db.session.add(group_perm)
            db.session.commit()
            flash('The new group ' + group_slugify(new_group.name, parent_id) + ' is added.')
            flash('You are set as the admin of the new group')

        except:
            flash('Could not create the group')
            return redirect(url_for('.create_group'))
    
    return render_template('groups/group_create.html', form=form, parent=None,course_group=0)


@groups_bp.route('<group_id>/create/', methods=['GET', 'POST'])
@login_required
@role_permission.require(http_exception=403)
@group_create_perm
def create_subgroup(group_id):
    flash(request.url)
    parent = Group.query.filter_by(id=group_id).one_or_none()
    form = GroupForm(request.form)
    parents_of_subgroups = db.session.query(Group).filter(
                            Group.permissions.any(type=PermType.groups)).all()
    form.target_groups.choices += ([(g.id, group_slugify(g.name,g.parent_id)) for g in parents_of_subgroups])
    if request.method == 'POST' and form.validate():
        group_name = slugify(form.name.data, separator='_')
        q = Group.query.filter_by(name=group_name, parent_id=group_id).one_or_none()
        if q:
            flash('The group ' + group_slugify(group_name, group_id) + ' already exists')
            return redirect(url_for('.create_subgroup', group_id=group_id))
        else:
            new_group = Group(name=group_name, parent_id=group_id)
            perm_selected = form.permissions.data

            for name, perm_type in PermType.__members__.items():
                if name in perm_selected:
                    perm = db.session.query(GroupPermission).filter(
                        GroupPermission.type == perm_type).first()
                    if not perm:
                        perm = GroupPermission(type=perm_type)
                        db.session.add(perm)
                
                    new_group.permissions.append(perm)
            
        course_perm,group_perms = None, None
        if new_group.parent_id is None or 'self_admin' in perm_selected:
            new_group.self_admin = True
        else:
            new_group.self_admin = False
        
        if 'courses' in perm_selected:
            course_prefix = form.course_prefix.data.upper()
            course_pattern = course_prefix + '-[A-Za-z][0-9][0-9][0-9][0-9]'
            course_perm = CreateCoursePerm(group=new_group,pattern=course_pattern)
        
        if 'groups' in perm_selected:
            parent_group_ids = form.target_groups.data
            if len(parent_group_ids) == 0:
                flash('You must choose a parent group')
                return redirect(url_for('.create_group'))
            group_perms = []
            for g_id in parent_group_ids:
                if g_id==0:
                    group_perm = CreateGroupPerm(group=new_group,target_group=new_group)
                else:
                    # target_group = db.session.query(Group).filter_by(id=g_id).one_or_none()
                    # group_perm = CreateGroupPerm(group=new_group,target_group=target_group)
                    group_perm = CreateGroupPerm(group=new_group,target_group_id=g_id)
                group_perms.append(group_perm)
        try:
            flash(form.data)
            new_group.members.append(current_user)
            db.session.add(new_group)
            if course_perm: 
                db.session.add(course_perm)
            if group_perms:
                for group_perm in group_perms:
                    db.session.add(group_perm)
            db.session.commit()
            flash('The new group ' + group_slugify(new_group.name, parent.id) + ' is added.')
            flash('You are set as the admin of the new group')
            if 'from_course' in request.url:
                return redirect(url_for('.create_subgroup',group_id=group_id)+'?from_course=true'+'&sucess=true'+'&group_id='+str(new_group.id))

        except:
            flash('Could not create the group')

    return render_template('groups/group_create.html', form=form, parent=parent)
    

@groups_bp.route('delete/<group_id>/', methods=['POST'])
@login_required
@role_permission.require(http_exception=403)
@group_edit_del_perm
def delete_group(group_id):
    group = db.session.query(Group).filter_by(id=group_id).one_or_none()
    # create_group_perms = db.session.query(CreateGroupPerm).filter(db.or_(
    #                     CreateGroupPerm.group_id==group.id,CreateGroupPerm.target_group_id==group.id)).all()
    
    group_slug = group_slugify(group.name, group.parent_id)
    # for perm in create_group_perms:
    #     db.session.delete(perm)
    db.session.delete(group)
    db.session.commit() 
    flash('The group ' + group_slug + ' has been deleted')
    # except:
    #     flash('Error occurs when trying to remove the group')
    #     return redirect(request.referrer)

    return redirect(request.referrer)


@groups_bp.route('edit/<group_id>/', methods=['GET', 'POST'])
@login_required
@role_permission.require(http_exception=403)
@group_edit_del_perm
def edit_group(group_id):
    group = db.session.query(Group).filter_by(id=group_id).one_or_none()
    flash(group.name)
    group_slug = group_slugify(group.name, group.parent_id)
    permissions = [perm.type.name for perm in group.permissions]
    form = GroupForm(request.form)
    form.name.label = "New group name"
    form.parent_path.label = "New parent path"
    form.permissions.label = 'Update permission'
    if request.method == 'POST' and form.validate():
        if request.form['edit'] == 'update parent path':

            new_parent_id = query_parent_id(form.parent_path.data)
            if new_parent_id == -1:
                flash('No such parent path!')
                return redirect(url_for('.edit_group', group_id=group.id))

            elif new_parent_id == group.parent_id:
                flash('No changes to make for the group')
                return redirect(url_for('.edit_group', group_id=group.id))
            else:
                q = db.session.query(Group).filter_by(id=new_parent_id).one_or_none()
                if (q.parent is None) or (current_user not in q.members):
                    flash("You can not change the group to this parent path because of the permission limitation")
                    return redirect(url_for('.list_my_groups'))
                else:
                    q2 = db.session.query(Group).filter_by(name=group.name,
                                                           parent_id=new_parent_id).one_or_none()
                    if q2:
                        flash('A group with the same name has been under the same parent')
                        return redirect(url_for('.edit_group', group_id=group.id))
                    group.parent_id = new_parent_id

        elif request.form['edit'] == 'rename':
            new_name = slugify(form.name.data, separator='_')
            if new_name == '':
                flash('The name could not be empty!')
                return redirect(url_for('.edit_group', group_id=group.id))
            elif new_name == group.name:
                flash('No changes to make for the group')
                return redirect(url_for('.edit_group', group_id=group.id))
            else:
                q = db.session.query(Group).filter_by(name=new_name,
                                                      parent_id=group.parent_id).one_or_none()

                if q:
                    flash('A group with the same name has been under the same parent')
                    return redirect(url_for('.edit_group', group_id=group.id))
                else:
                    group.name = new_name

        elif request.form['edit'] == 'update permissions':
            perm_origin = [perm.type.name for perm in group.permissions]
            perm_new = form.permissions.data
            flash(perm_new)


            for name, perm_type in PermType.__members__.items():
                if (name not in perm_origin) and (name in perm_new):
                    perm = db.session.query(GroupPermission).filter(
                        GroupPermission.type == perm_type).first()
                    if not perm:
                        perm = GroupPermission(type=perm_type)
                    group.permissions.append(perm)

                if (name in perm_origin) and (name not in perm_new):
                    perm = db.session.query(GroupPermission).filter(
                        GroupPermission.type == perm_type).first()
                    group.permissions.remove(perm)

            if 'self_admin' in perm_new:
                group.self_admin = True
            else:
                group.self_admin = False
                self_group_perm = db.session.query(CreateGroupPerm).filter(
                                    CreateGroupPerm.group_id==group.id,
                                    CreateGroupPerm.target_group_id==group.id).one_or_none()
                if self_group_perm:
                    db.session.delete(self_group_perm)
                    db.session.commit()
        try:
            group.save()
            flash('The group ' + group_slugify(group.name, group.parent_id) + ' is edited successfully')
            return redirect(url_for('.list_my_groups'))
        except:
            flash('The group edit failed')
            return redirect(url_for('.edit_group', group_id=group.id))

    return render_template('groups/group_edit.html', form=form, group_slug=group_slug, permissions=permissions)


@groups_bp.route('<group_id>/members/', methods=['GET'])
@login_required
@role_permission.require(http_exception=403)
def list_members(group_id):
    title = "Member list"
    group = Group.query.filter_by(id=group_id).one_or_none()
    if group is None:
        flash('There is no such group')
        return redirect(request.referrer)
    else:
        members = group.members

    return render_template('members/member_list.html', title=title, user=current_user, group=group, members=members)


@groups_bp.route('/<group_id>/add_members/', methods=['GET'])
@login_required
@role_permission.require(http_exception=403)
def list_users(group_id):
    group = db.session.query(Group).filter_by(id=group_id).one_or_none()

    conditions = []
    for role in ['Instructor', 'Mentor', 'Teacher', 'TeachingAssistant', 'TA']:
        conditions.append(User.roles.contains(role))
    available_users = db.session.query(User).filter(db.or_(*conditions),
                                                    db.not_(User.groups.any(Group.id == group.id))).all()

    return render_template('members/members_add.html', group=group, users=available_users)


@groups_bp.route('<group_id>/members/add/', methods=['POST'])
@login_required
@role_permission.require(http_exception=403)
@membership_perm
def add_member(group_id):
    group = db.session.query(Group).filter_by(id=group_id).one_or_none()

    try:
        user_id = request.form['user']
        conditions = []
        for role in ['Instructor', 'Mentor', 'Teacher', 'TeachingAssistant', 'TA']:
            conditions.append(User.roles.contains(role))

        new_member = db.session.query(User).filter(User.id == user_id,
                                                   db.or_(*conditions), ).one_or_none()
        if new_member is None:
            flash('No such a user')
            return redirect(request.referrer)
        group.members.append(new_member)
        db.session.commit()
        flash('The new member is added')
    except:
        flash('Could not add this user')
    return redirect(url_for('.list_users', group_id=group.id))


@groups_bp.route('/<group_id>/members/delete/', methods=['POST'])
@login_required
@role_permission.require(http_exception=403)
@membership_perm
def delete_member(group_id):
    group = db.session.query(Group).filter_by(id=group_id).one_or_none()

    try:
        user_id = request.form['user']
        new_member = db.session.query(User).filter_by(id=user_id).one_or_none()
        if new_member is None:
            flash('No such a user')
            return redirect(request.referrer)
        group.members.remove(new_member)
        db.session.commit()
        flash('The member is removed')
        return redirect(url_for('.list_members', group_id=group.id))
    except:
        flash('Could not remove this user')
        return redirect(url_for('.list_members', group_id=group.id))

    return redirect(request.referrer)


@groups_bp.route('/test/', methods=['POST','GET'])
@login_required
def test():
    form = GroupForm(request.form)
    
    parents_of_subgroups = db.session.query(Group).filter(
                            Group.permissions.any(type=PermType.groups)).all()
    form.target_groups.choices += ([(g.id, group_slugify(g.name,g.parent_id)) for g in parents_of_subgroups])

    if request.method == 'POST' and form.validate():
        group_name = slugify(form.name.data, separator='_')
        parent_id = query_parent_id(form.parent_path.data)

        if parent_id == -1:
            flash('No such a parent path ' + form.parent_path.data)
            raise Exception('parent path error!')
            

        parent = Group.query.filter_by(id=parent_id).one_or_none()
        if parent and current_user not in parent.members:
            flash('You are not the member of this group, could not create subgroups')
            raise Exception('permission Error!')

        q = Group.query.filter_by(name=group_name, parent_id=parent_id).one_or_none()
        if q is not None:
            flash('The group ' + group_slugify(group_name, parent_id) + ' already exists.')
            raise Exception('group Error!')

        new_group = Group(name=group_name, parent_id=parent_id)
        perm_selected = form.permissions.data

        for name, perm_type in PermType.__members__.items():
            if name in perm_selected:
                perm = db.session.query(GroupPermission).filter(
                    GroupPermission.type == perm_type).first()
                if not perm:
                    perm = GroupPermission(type=perm_type)
                    db.session.add(perm)
                    db.session.commit()
                new_group.permissions.append(perm)

        course_perm,group_perms = None, None
        if new_group.parent_id is None or 'self_admin' in perm_selected:
            new_group.self_admin = True
        else:
            new_group.self_admin = False
        
        if 'groups' in perm_selected:
            parent_group_ids = form.target_groups.data
            if len(parent_group_ids) == 0:
                flash('You must choose a parent group')
                raise Exception(' no parent Error!')
            group_perms = []
            for g_id in parent_group_ids:
                if g_id==0:
                    group_perm = CreateGroupPerm(group=new_group,target_group=new_group)
                else:
                    target_group = db.session.query(Group).filter_by(id=g_id).one_or_none()
                    group_perm = CreateGroupPerm(group=new_group,target_group=target_group)
                    # group_perm = CreateGroupPerm(group=new_group,target_group_id=g_id)
                group_perms.append(group_perm)
        try:
            new_group.members.append(current_user)
            db.session.add(new_group)
            if course_perm: 
                db.session.add(course_perm)
            if group_perms:
                for group_perm in group_perms:
                    db.session.add(group_perm)
            db.session.commit()
            flash('The new group ' + group_slugify(new_group.name, parent_id) + ' is added.')
            flash('You are set as the admin of the new group')
        except:
            flash('Could not create the group')
            raise Exception('Could not create the group')

    return jsonify(group_id=new_group.id)