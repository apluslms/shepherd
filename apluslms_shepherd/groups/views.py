from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user, logout_user
from apluslms_shepherd.groups.forms import GroupForm
from apluslms_shepherd.groups.models import Group,db,association_table
from apluslms_shepherd.auth.models import User
from sqlalchemy.exc import IntegrityError
from slugify import slugify

groups_bp = Blueprint('groups', __name__, url_prefix='/groups')


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


@groups_bp.route('/', methods=['GET'])
@login_required
def list_all_groups():

    title = "Group list"
    roots = Group.query.filter_by(parent_id=None).all()
    # full_tree = []
    # for root in roots:
    #     full_tree.append(root.drilldown_tree()[0])
    # return render_template('test.html', title=title, groups=full_tree)
    return render_template('groups/group_list.html', title=title, roots=roots,group=None)


@groups_bp.route('<group_id>/subgroups/', methods=['GET'])
@login_required
def list_subgroups(group_id):
    group = db.session.query(Group).filter_by(id=group_id).one_or_none()
    if group is None:
        flash('There is no such group')
        # return redirect(url_for('.list_groups'))
        return redirect(request.referrer)
    else:
        title = 'Group: ' + group_slugify(group.name,group.parent_id)
        roots = Group.query.filter_by(parent_id=group.id).all()
    # full_tree = []
    # for root in roots:
    #     full_tree.append(root.drilldown_tree()[0])
    # return render_template('test.html', title=title, groups=full_tree)
    return render_template('groups/group_list.html', title=title, roots=roots,group=group)


@groups_bp.route('/my_groups/', methods=['GET'])
@login_required
def list_my_groups():
    title = "My Groups"
    # groups = (db.session.query(Group).join(association_table).\
    #         filter(association_table.columns.user_id==current_user.id).all())
    # groups = db.session.query(Group).filter(Group.members.any(User.id==current_user.id).all()
    groups = Group.query.join(Group.members).filter(User.id == current_user.id).all()
    group_slugs = [group_slugify(g.name,g.parent_id) for g in groups]
    return render_template('groups/my_groups.html', title=title, groups=zip(groups,group_slugs))


@groups_bp.route('create/', methods=['GET','POST'])
@login_required
def create_group():
    form = GroupForm(request.form)
    if form.validate() and request.method == 'POST':
       
        group_name = slugify(form.name.data,separator='_')
        parent_id = query_parent_id(form.parent_path.data)

        if parent_id == -1:
            flash('No such a parent path ' + form.parent_path.data)
            return redirect(url_for('.create_group'))

        parent = Group.query.filter_by(id=parent_id).one_or_none()
        if current_user not in parent.members:
            flash('You are not the member of this group, could not create subgroups')
            return redirect(url_for('.create_group'))

        q = Group.query.filter_by(name=group_name,parent_id=parent.id).one_or_none()

        if q is not None:
            flash('The group '+ group_slugify(group_name,parent.id) +' already exists.')
            return redirect(url_for('.create_group'))
        
        new_group = Group(name=group_name,parent_id=parent.id)
        try:
            new_group.save()
            flash('The new group '+ group_slugify(new_group.name,parent_id) +' is added.')
            try:
                new_group.members.append(current_user)
                db.session.commit()
                flash('You are set as the admin of the new group')
            except:
                flash('Failed to set you as the admin of the new group')
                return redirect(request.referrer)
        except:
            flash('Could not create the group')
            return redirect(url_for('.create_group'))

    return render_template('groups/group_create.html', form=form,parent=None)


@groups_bp.route('<group_id>/create/', methods=['GET','POST'])
@login_required
def create_subgroup(group_id):
    parent = Group.query.filter_by(id=group_id).one_or_none()
    if parent is None:
        flash('No such a group')
        return redirect(request.referrer)

    # check = Group.query.join(Group.members).filter(Group.id == group_id, 
    #                                         User.id == current_user.id).one_or_none()
    # if check:
    if current_user in parent.members:
        form = GroupForm(request.form)
        if form.validate() and request.method == 'POST':
            
            group_name = slugify(form.name.data,separator='_')
            q = Group.query.filter_by(name=group_name,parent_id=group_id).one_or_none()
            if q is not None:
                flash('The group '+ group_slugify(group_name,group_id) +' already exists')
                return redirect(url_for('.create_subgroup',group_id=group_id))
            else:
                new_group = Group(name=group_name,parent_id=group_id)
                try:
                    new_group.save()
                    flash('The new group '+ group_slugify(group_name,group_id) +' is created successfully')
                    try:
                        new_group.members.append(current_user)
                        db.session.commit()
                        flash('You are set as the admin of the new group')
                    except:
                        flash('Failed to set you as the admin of the new group')
                        return redirect(request.referrer)
                except:
                    flash('Could not create the group ')
                    return redirect(url_for('.create_subgroup',group_id=group_id))
            return redirect(url_for('.list_my_groups'))
    else:
        flash('You are not the member of this group, could not create subgroups')
        return redirect(request.referrer)

    return render_template('groups/group_create.html', form=form,parent=parent)



@groups_bp.route('delete/<group_id>/', methods=['POST'])
@login_required
def delete_group(group_id):

    group = db.session.query(Group).filter_by(id=group_id).one_or_none()
    if group is None:
        flash('There is no such group')
        return redirect(request.referrer)
    else:
        check = Group.query.join(Group.members).filter(Group.id == group.parent_id, 
                                                    User.id == current_user.id).one_or_none()
        if check:
            try:
                group_slug = group_slugify(group.name,group.parent_id)
                group.delete()
                flash('The group '+group_slug+' has been deleted')
            except:
                flash('Error occurs when trying to remove the group')
                return redirect(request.referrer)
    
        else:
            flash("You don't have the permission to delete this group!")
            return redirect(request.referrer)
        
    return redirect(request.referrer)


@groups_bp.route('edit/<group_id>/', methods=['GET','POST'])
@login_required
def edit_group(group_id):

    group = db.session.query(Group).filter_by(id=group_id).one_or_none()
    if group is None:
        flash('There is no such group')
        return redirect(request.referrer)
    if current_user not in group.members:
        flash("You don't have the permission to delete this group!")
        return redirect(request.referrer)
    
    group_slug = group_slugify(group.name,group.parent_id)
    form = GroupForm(request.form)
    form.name.label = "New group name"
    form.parent_path.label = "New parent path"
    if form.validate() and request.method == 'POST':
        if request.form['edit'] == 'update parent path':

            new_parent_id = query_parent_id(form.parent_path.data)
            if new_parent_id == -1:
                flash('No such parent path!')
                return redirect(url_for('.edit_group',group_id=group.id)) 

            elif new_parent_id == group.parent_id:
                flash('No changes to make for the group')
                return redirect(url_for('.edit_group',group_id=group.id))  
            else:
                q = db.session.query(Group).filter_by(name=group.name,
                                            parent_id=new_parent_id).one_or_none()
                if q:
                    flash('A group with the same name has been under the same parent')
                    return redirect(url_for('.edit_group',group_id=group.id))  
                else:
                    group.parent_id = new_parent_id
                    try: 
                        group.save()
                        flash('The group '+group_slugify(group.name,group.parent_id)+' is edited successfully')
                        return redirect(url_for('.edit_group',group_id=group.id))  
                    except:
                        flash('The group edit failed')  
                        return redirect(url_for('.edit_group',group_id=group.id))  

        elif request.form['edit'] == 'rename':
            new_name = slugify(form.name.data,separator='_')
            if new_name == '':
                flash('The name could not be empty!')
                return redirect(url_for('.edit_group',group_id=group.id))  
            elif new_name == group.name:
                flash('No changes to make for the group')
                return redirect(url_for('.edit_group',group_id=group.id))  
            else:
                q = db.session.query(Group).filter_by(name=new_name,
                                            parent_id=group.parent_id).one_or_none()

                if q:
                    flash('A group with the same name has been under the same parent')
                    return redirect(url_for('.edit_group',group_id=group.id))  
                else:
                    group.name = new_name
                    try: 
                        group.save()
                        flash('The group '+group_slugify(group.name,group.parent_id)+' is edited successfully')
                        return redirect(url_for('.edit_group',group_id=group.id))  
                    except:
                        flash('The group edit failed')  
                        return redirect(url_for('.edit_group',group_id=group.id))  

    return render_template('groups/group_edit.html', form=form,group_slug=group_slug) 



@groups_bp.route('<group_id>/members/', methods=['GET'])
@login_required
def list_members(group_id):
    title = "Member list"
    group = Group.query.filter_by(id=group_id).one_or_none()
    if group is None:
        flash('There is no such group')
        return redirect(request.referrer)
    else:
        members = group.members

    return render_template('members/member_list.html',title=title,group=group,members=members)


@groups_bp.route('/<group_id>/add_members/', methods=['GET'])
@login_required
def list_users(group_id):

    group = db.session.query(Group).filter_by(id=group_id).one_or_none()
    if group is None:
        flash('There is no such group')
        return redirect(request.referrer)
    if current_user not in group.members:
        flash("You don't have the permission to manage members")
        return redirect(request.referrer)
    
    available_users = db.session.query(User).filter(User.roles.in_(['Instructor','Teacher','Assistant']),\
                            db.not_(User.groups.any(Group.id==group.id))).all()
            
    return render_template('members/members_add.html', group=group, users=available_users) 


@groups_bp.route('<group_id>/members/add/', methods=['POST'])
@login_required
def add_member(group_id):

    group = db.session.query(Group).filter_by(id=group_id).one_or_none()
    if group is None:
        flash('There is no such group')
        return redirect(url_for('.list_my_groups'))
    if current_user not in group.members:
        flash("You don't have the permission to manage members")
        return redirect(url_for('.list_my_groups'))
    try:
        user_id = request.form['user']
        new_member = db.session.query(User).filter(User.id==user_id,\
                                            User.roles.in_(['Instructor','Teacher','Assistant'])).one_or_none()
        if new_member is None:
            flash('No such a user')
            return redirect(request.referrer)
        group.members.append(new_member)
        db.session.commit()
        flash('The new member is added')
        return redirect(url_for('.list_users',group_id=group.id))
        
    except:
        flash('Could not add this user')
        return redirect(url_for('.list_users',group_id=group.id))
            
    return redirect(url_for('.list_users',group_id=group.id))

@groups_bp.route('/<group_id>/members/delete/', methods=['POST'])
@login_required
def delete_member(group_id):

    group = db.session.query(Group).filter_by(id=group_id).one_or_none()
    if group is None:
        flash('There is no such group')
        return redirect(url_for('.list_my_groups'))
    if current_user not in group.members:
        flash("You don't have the permission to manage members")
        return redirect(request.referrer)
    try:
        user_id = request.form['user']
        new_member = db.session.query(User).filter_by(id=user_id).one_or_none()
        if new_member is None:
            flash('No such a user')
            return redirect(request.referrer)
        group.members.remove(new_member)
        db.session.commit()
        flash('The member is removed')
        return redirect(url_for('.list_members',group_id=group.id))
        
    except:
        flash('Could not remove this user')
        return redirect(url_for('.list_members',group_id=group.id))
            
    return redirect(request.referrer)