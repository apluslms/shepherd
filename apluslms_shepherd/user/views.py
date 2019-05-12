from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import LoginManager,login_required, logout_user, current_user, login_user
from apluslms_shepherd.user.forms import RegistrationForm,LoginForm
from apluslms_shepherd.user.models import Member,db
from apluslms_shepherd.groups.views import groups_bp 
from apluslms_shepherd.auth.models import User,load_user


user_bp = Blueprint('user', __name__,url_prefix='/')


@user_bp.route('register/', methods=['GET', 'POST'])
def register():
    form = RegistrationForm(request.form)
    if request.method == 'POST' and form.validate():
        email = form.email.data
        q = db.session.query(Member).filter_by(email=email).one_or_none()
        if q:
            flash('The email address has been used')
            return redirect(url_for('.register'))

        user = User(form.full_name.data,
                    form.display_name.data,
                    form.sorting_name.data,
                    form.email.data,
                    form.password.data)
        try:
            db.session.add(user)
            db.session.commit()
            flash('Thanks for registration')
            return redirect('.login')
        except:
            flash('Sorry, failed to register')
            return redirect(url_for('.register'))
            
    return render_template('user/register.html', form=form)


@user_bp.route('login/', methods=['GET', 'POST'])
def login():
    form = LoginForm(request.form)
    if request.method == 'POST' and form.validate():
        email = form.email.data
        user = db.session.query(Member).filter_by(email=email).one_or_none()

        if user is None:
            flash('The email has not registered yet')
            return redirect(url_for('.login'))

        elif user.id == current_user.id:
            flash("You've logged in")
            return redirect(url_for('groups.list_group'))

        else:
            if user.password == form.password.data:
                login_user(user)
                flash("You've been logged in successfully.",'success')
                return redirect(url_for('groups.list_groups'))
            else:
                flash("The email and password you've entered don't match." , "error")
                return redirect(url_for('.login'))

    return render_template('user/login.html', form=form)


@user_bp.route('logout/', methods=['GET'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('.login'))
    