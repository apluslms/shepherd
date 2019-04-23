import datetime

from shepherd.auth.models import db
from flask import current_app


class CourseRepository(db.Model):
    key = db.Column(db.String(50), unique=True, primary_key=True)
    git_origin = db.Column(db.String(255), default='')
    name = db.Column(db.String(50), default='')
    owner = db.Column(db.String(current_app.config['USER_NAME_LENGTH']))
    instance = db.relationship('CourseInstance', backref='course_repository', lazy=True)


class CourseInstance(db.Model):
    key = db.Column(db.String(50), primary_key=True)
    course_key = db.Column(db.String(255), db.ForeignKey('course_repository.key'), nullable=False)
    branches = db.Column(db.String, default='master')

    def get_branches(self):
        return [each for each in self.branches.split(' ')]
