from flask import flash
from apluslms_shepherd.extensions import db
from flask_login import UserMixin, login_user, LoginManager
from apluslms_shepherd.config import DevelopmentConfig


login_manager = LoginManager()


@login_manager.user_loader
def load_user(id):
    user = User.query.filter_by(id=id).first()
    return user


def write_user_to_db(*args, **kwargs):
    user_id = kwargs['user_id']
    user = User.query.filter_by(id=user_id).first()

    if user is None:
        if not DevelopmentConfig.CREATE_UNKNOWN_USER:
            return None
            # create new
        user = User(id=user_id, email=kwargs['email'], display_name=kwargs['display_name'], sorting_name=kwargs['sorting_name'], is_active=True)
    # if exist, update
    else:
        user.sorting_name = kwargs['sorting_name']
        user.display_name = kwargs['display_name']
        user.email = kwargs['email']
    # user.is_staff = staff_roles and not roles.isdisjoint(staff_roles) or False
    db.session.add(user)
    db.session.commit()
    login_user(user)
    flash('Login Success!')


class User(db.Model, UserMixin):
    id = db.Column(db.String(DevelopmentConfig.USER_NAME_LENGTH), primary_key=True, unique=True)
    email = db.Column(db.String(DevelopmentConfig.EMAIL_LENGTH), unique=True, nullable=False)
    display_name = db.Column(db.String(DevelopmentConfig.FIRST_NAME_LENGTH))
    sorting_name = db.Column(db.String(DevelopmentConfig.LAST_NAME_LENGTH))
    full_name = db.Column(db.String(DevelopmentConfig.LAST_NAME_LENGTH + DevelopmentConfig.FIRST_NAME_LENGTH))
    is_active = db.Column(db.Boolean, default=True)
