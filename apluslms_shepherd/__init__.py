from flask import Flask,request,session,redirect,url_for,flash
from flask_lti_login import lti, lti_login_authenticated
from flask_migrate import Migrate
from flask_login import current_user
from apluslms_shepherd import config
from apluslms_shepherd.extensions import celery, db, make_celery
from flask_principal import Principal, Identity, AnonymousIdentity, \
    identity_changed, identity_loaded, RoleNeed, UserNeed
from apluslms_shepherd.groups.utils import GroupManageNeed,CourseManageNeed
from apluslms_shepherd.groups.models import PermType

__version__ = '0.1'


def create_app():
    app = Flask(__name__)
    app.config.from_object(config.DevelopmentConfig)
    app.jinja_env.add_extension('jinja2.ext.loopcontrols')
    with app.app_context():
        from apluslms_shepherd.auth.models import write_user_to_db, login_manager
        from apluslms_shepherd.views import main_bp
        from apluslms_shepherd.auth.views import auth_bp
        from apluslms_shepherd.courses.views import course_bp
        from apluslms_shepherd.webhooks.view import webhooks_bp
        from apluslms_shepherd.groups.views import groups_bp
        login_manager.init_app(app=app)
        db.init_app(app=app)
        migrate = Migrate(app, db, render_as_batch=True)
        lti_login_authenticated.connect(write_user_to_db)
        # Flask-Principal: ---  Setup ------------------------------------
        principals = Principal(app)
        principals.init_app(app)
        #-----------------------------------------------------------------
        app.register_blueprint(main_bp)
        app.register_blueprint(course_bp)
        app.register_blueprint(lti)
        app.register_blueprint(auth_bp)
        app.register_blueprint(webhooks_bp)
        app.register_blueprint(groups_bp)

        
        @identity_loaded.connect_via(app)
        def on_identity_loaded(sender, identity):
            # Set the identity user object
            identity.user = current_user

            # Add the UserNeed to the identity
            if hasattr(current_user, 'id'):
                identity.provides.add(UserNeed(current_user.id))

            # Update the identity with the role that the user provides
            if hasattr(current_user, 'roles'):
                for role in current_user.roles.split(','):
                    identity.provides.add(RoleNeed(role))

            if hasattr(current_user, 'groups'):
                for group in current_user.groups:
                    for perm in group.permissions:
                        if perm.type == PermType.groups:
                            identity.provides.add(GroupManageNeed(group_id=str(group.id)))
                            # identity.provides.add(GroupNeed(action='create',group_id=group.id))

                        if perm.type == PermType.courses:
                            identity.provides.add(CourseManageNeed(group_id=str(group.id)))
                            # identity.provides.add(CourseNeed(action='create',group_id=group.id))

            app.logger.info(identity)

        @app.errorhandler(403)
        def page_not_found(e):
            session['redirected_from'] = request.url
            flash('Access Forbidden')
            return redirect(request.referrer)
        
    return app
