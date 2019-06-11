from flask import Flask,request,session,redirect,url_for,flash
from flask_lti_login import lti, lti_login_authenticated
from flask_migrate import Migrate

from flask_login import current_user

from apluslms_shepherd import config

from apluslms_shepherd.extensions import celery, db, make_celery

from flask_principal import Principal, identity_loaded, RoleNeed, UserNeed
from apluslms_shepherd.groups.models import PermType    
from apluslms_shepherd.groups.utils import SelfAdminNeed, SubgroupCreateNeed, CourseCreateNeed


__version__ = '0.1'


def create_app():
    app = Flask(__name__)
    app.config.from_object(config.DevelopmentConfig)
    # adds jinja2 support for break and continue in loops
    app.jinja_env.add_extension('jinja2.ext.loopcontrols')
    with app.app_context():
        from apluslms_shepherd.auth.models import write_user_to_db, login_manager
        from apluslms_shepherd.views import main_bp
        from apluslms_shepherd.auth.views import auth_bp
        from apluslms_shepherd.courses.views import course_bp
        from apluslms_shepherd.build.views import build_log_bp
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
        app.register_blueprint(build_log_bp)
        app.register_blueprint(course_bp)
        app.register_blueprint(lti)
        app.register_blueprint(auth_bp)
        app.register_blueprint(webhooks_bp)
        app.register_blueprint(groups_bp)

        
        # Add info to the Identity instance
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

            # The User model has a list of groups the user
            # has authored, add the needs to the identity
            if hasattr(current_user, 'groups'):
                for group in current_user.groups:  # For each group

                    if group.self_admin: # Check whether it is self-admin
                        identity.provides.add(SelfAdminNeed(group_id=str(group.id)))

                    for perm in group.permissions:  # Check its permissions
                        # Add the CreateSubgroup need
                        if perm.type == PermType.subgroups:
                            identity.provides.add(SubgroupCreateNeed(group_id=str(group.id)))
                        # Add the CreateCourse need
                        if perm.type == PermType.courses:
                            identity.provides.add(CourseCreateNeed(group_id=str(group.id)))

            app.logger.info(identity)


        # Handle HTTP 403 error
        @app.errorhandler(403)
        def access_forbidden(e):
            session['redirected_from'] = request.url
            flash('Access Forbidden')
            return redirect('/')
        
    return app
