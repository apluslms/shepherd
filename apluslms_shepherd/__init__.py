from flask import Flask
from flask_lti_login import lti, lti_login_authenticated
from flask_migrate import Migrate

from apluslms_shepherd import config
from apluslms_shepherd.extensions import celery, db, make_celery

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
        app.register_blueprint(main_bp)
        app.register_blueprint(course_bp)
        app.register_blueprint(lti)
        app.register_blueprint(auth_bp)
        app.register_blueprint(webhooks_bp)
        app.register_blueprint(groups_bp)
    return app
