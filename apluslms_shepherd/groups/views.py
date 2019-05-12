from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user, logout_user
from apluslms_shepherd.groups.forms import GroupForm
from apluslms_shepherd.groups.models import Group,db
from sqlalchemy.exc import IntegrityError
from slugify import slugify

groups_bp = Blueprint('groups', __name__, url_prefix='/groups/')


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


def query_group_id(group_path):
    parent_id = None
    if group_path == '':
        return parent_id

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
def list_groups():
    title = "Group list"
    roots = Group.query.filter_by(parent_id=None).all()
    # full_tree = []
    # for root in roots:
    #     full_tree.append(root.drilldown_tree()[0])
    # return render_template('test.html', title=title, groups=full_tree)
    return render_template('groups/group_list.html', title=title, roots=roots)


@groups_bp.route('create/', methods=['GET','POST'])
def create_group():

    form = GroupForm(request.form)
    if form.validate() and request.method == 'POST':

        group_name = slugify(form.name.data,separator='_')
        parent_id = query_group_id(form.parent_path.data)

        if parent_id == -1:
            flash('No such a parent path ' + form.parent_path.data)
            return redirect(url_for('.create_group'))

        q = Group.query.filter_by(name=group_name,parent_id=parent_id).one_or_none()

        if q is not None:
            flash('The group '+ group_slugify(group_name,parent_id) +' already exists.')
        else:
            new_group = Group(name=group_name,parent_id=parent_id)
            try:
                new_group.save()
                flash('The new group '+ group_slugify(new_group.name,parent_id) +' is added.')
            except:
                flash('Could not create the group '+ group_slugify(group_name,parent_id) )

        return redirect(url_for('.create_group'))

    return render_template('groups/group_create.html', form=form)


@groups_bp.route('delete/<group_id>/', methods=['POST'])
def delete_group(group_id):

    group = db.session.query(Group).filter_by(id=group_id).one_or_none()
    if group is None:
        flash('There is no such group')
    else:
        try:
            group_slug = group_slugify(group.name,group.parent_id)
            group.delete()
            flash('The group '+group_slug+' has been deleted')
        except:
            flash('Error occurs when trying to remove the group')
    return redirect(url_for('.list_groups'))  


@groups_bp.route('edit/<group_id>/', methods=['GET','POST'])
def edit_group(group_id):
    group = db.session.query(Group).filter_by(id=group_id).one_or_none()
    if group is None:
        group_slug = None
    else:
        group_slug = group_slugify(group.name,group.parent_id)

    if group is None:
        flash('There is no such group')
        return redirect(url_for('.list_groups'))
    else:
        form = GroupForm(request.form,obj=group)
        form.parent_path.label = "New parent path"
        if form.validate() and request.method == 'POST':
            new_parent_id = query_group_id(form.parent_path.data)

            if new_parent_id == group.parent_id:
                flash('No changes to make for the group')
                return redirect(url_for('.edit_group',group_id=group.id))  

            q = db.session.query(Group).filter_by(name=group.name,parent_id=new_parent_id).one_or_none()
            if q:
                flash('A group with the same name has been under the same parent')
                return redirect(url_for('.edit_group',group_id=group.id))  
            else:
                group.parent_id = new_parent_id
                try: 
                    group.save()
                    flash('The group '+group_slugify(group.name,group.parent_id)+' is edited successfully')
                except:
                    flash('The group edit failed')  
                    return redirect(url_for('.edit_group',group_id=group.id))  
    return render_template('groups/group_edit.html', form=form,group_slug=group_slug) 