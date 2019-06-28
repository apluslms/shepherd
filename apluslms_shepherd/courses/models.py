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
