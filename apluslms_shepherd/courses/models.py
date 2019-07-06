# standard libs
from datetime import  datetime

# 3rd party libs
import jwt
from flask import current_app

# from this project
from apluslms_shepherd.extensions import db
from apluslms_shepherd.groups.models import gc_table


class CourseInstance(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    course_key = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(50), default='')
    owners = db.relationship("Group", secondary=gc_table, backref=db.backref('courses', lazy='dynamic'))
    instance_key = db.Column(db.String(50), nullable=False)
    git_origin = db.Column(db.String(255), db.ForeignKey('git_repository.origin'), default='')
    secret_token = db.Column(db.String(127))
    config_filename = db.Column(db.String(127))
    branch = db.Column(db.String, default='master')
    jwt_token = db.Column(db.String)

    def generate_jwt_token(self):
        """
        Generates a JSON Web Token
        """
        course_instance_pair = (self.course_key.replace('_', '__'),
                                self.instance_key.replace('_', '__'))
        sub = '_'.join(course_instance_pair)

        payload = {
            'sub': sub,
            'iat': datetime.utcnow(),
            'iss': current_app.config['JWT_ISSUER']
        }

        jwt_private_key = "\n".join([l.lstrip() for l in current_app.config["JWT_PRIVATE_KEY"].split("\n")])

        token = jwt.encode(
                payload,
                jwt_private_key,
                algorithm=current_app.config['JWT_ALGORITHM'])

        return token.decode('utf-8')

