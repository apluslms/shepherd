import datetime

from shepherd.auth.models import db
from flask import current_app


class CourseRepository(db.Model):
    key = db.Column(db.String(50), unique=True, primary_key=True)
    git_origin = db.Column(db.String(255), default='')
    git_branch = db.Column(db.String(50), default='')
    name = db.Column(db.String(50), default='')
    owner = db.Column(db.String(current_app.config['USER_NAME_LENGTH']))
    updates = db.relationship('CourseRepositoryUpdate', backref='course_repository', lazy=True)


class CourseRepositoryUpdate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.String(255), db.ForeignKey('course_repository.key'), nullable=False)
    request_ip = db.Column(db.String(50), default='')
    request_time = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_time = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated = db.Column(db.Boolean, default=False)
    log = db.Column(db.Text, default="")

