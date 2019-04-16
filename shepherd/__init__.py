from flask import Flask
from flask_lti_login import lti, lti_login_authenticated

from shepherd import config

__version__ = '0.1'


def create_app():
    app = Flask(__name__)
    app.config.from_object(config.DevelopmentConfig)
    with app.app_context():
        from shepherd.auth.models import write_user_to_db, db, login_manager
        from shepherd.views import main_bp
        from shepherd.auth.views import auth_bp
        from shepherd.courses.views import course_bp
        login_manager.init_app(app=app)
        db.init_app(app=app)
        db.create_all()
        lti_login_authenticated.connect(write_user_to_db)
        app.register_blueprint(main_bp)
        app.register_blueprint(course_bp)
        app.register_blueprint(lti)
        app.register_blueprint(auth_bp)
    return app
