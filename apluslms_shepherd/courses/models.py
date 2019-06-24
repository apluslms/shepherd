from apluslms_shepherd.extensions import db
from apluslms_shepherd.config import DevelopmentConfig
from apluslms_shepherd.groups.models import gc_table
class CourseRepository(db.Model):
    key = db.Column(db.String(50), unique=True, primary_key=True)
    name = db.Column(db.String(50), default='')
    owners = db.relationship("Group", secondary=gc_table,
                            backref=db.backref('courses', lazy='dynamic'))
    instance = db.relationship('CourseInstance', backref='course_repository', cascade="all,delete")


class CourseInstance(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    key = db.Column(db.String(50), nullable=False)
    course_key = db.Column(db.String(50), db.ForeignKey('course_repository.key'), nullable=False)
    git_origin = db.Column(db.String(255), default='')
    secret_token = db.Column(db.String(127))
    config_filename = db.Column(db.String(127))
    branch = db.Column(db.String, default='master')
    builds = db.relationship('Build', lazy='select', backref=db.backref('instance', lazy='joined'))
