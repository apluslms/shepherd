from flask import flash,current_app
from apluslms_shepherd.extensions import db
from flask_login import UserMixin, login_user, LoginManager,current_user
from apluslms_shepherd.config import DevelopmentConfig
from collections import namedtuple
from functools import partial
from flask_principal import Principal, Identity, AnonymousIdentity, identity_changed,\
    identity_loaded

login_manager = LoginManager()

@login_manager.user_loader
def load_user(id):
    user = User.query.filter_by(id=id).first()
    return user


def write_user_to_db(*args, **kwargs):
    user_id = kwargs['user_id']
    user = User.query.filter_by(id=user_id).first()
    if user is None:
        print('No such user')
        if not DevelopmentConfig.CREATE_UNKNOWN_USER:
            return None
        # create new
        user = User(id=user_id, email=kwargs['email'], display_name=kwargs['display_name'],
                    sorting_name=kwargs['sorting_name'], roles=kwargs['roles'], is_active=True)
    # if exist, update
    else:
        user.sorting_name = kwargs['sorting_name']
        user.display_name = kwargs['display_name']
        user.email = kwargs['email']
        user.roles = kwargs['roles']
    # user.is_staff = staff_roles and not roles.isdisjoint(staff_roles) or False
    db.session.add(user)
    db.session.commit()
    login_user(user)
    # Tell Flask-Principal the identity changed
    identity_changed.send(current_app._get_current_object(),
                            identity=Identity(user.id))
    flash('Login Success!')


class User(db.Model, UserMixin):
    id = db.Column(db.String(DevelopmentConfig.USER_NAME_LENGTH), primary_key=True, unique=True)
    email = db.Column(db.String(DevelopmentConfig.EMAIL_LENGTH), unique=True, nullable=False)
    display_name = db.Column(db.String(DevelopmentConfig.FIRST_NAME_LENGTH))
    sorting_name = db.Column(db.String(DevelopmentConfig.LAST_NAME_LENGTH))
    full_name = db.Column(db.String(DevelopmentConfig.LAST_NAME_LENGTH + DevelopmentConfig.FIRST_NAME_LENGTH))
    roles = db.Column(db.String(30))
    is_active = db.Column(db.Boolean, default=True)
