import datetime

from apluslms_shepherd.extensions import db
from apluslms_shepherd.config import DevelopmentConfig


class CourseRepository(db.Model):
    key = db.Column(db.String(50), unique=True, primary_key=True)
    name = db.Column(db.String(50), default='')
    owner = db.Column(db.String(DevelopmentConfig.USER_NAME_LENGTH))
    instance = db.relationship('CourseInstance', backref='course_repository', cascade="all,delete")


class CourseInstance(db.Model):
    key = db.Column(db.String(50), primary_key=True)
    course_key = db.Column(db.String(50), db.ForeignKey('course_repository.key'), nullable=False, primary_key=True)
    git_origin = db.Column(db.String(255), default='')
    secret_token = db.Column(db.String(127))
    branch = db.Column(db.String, default='master')
