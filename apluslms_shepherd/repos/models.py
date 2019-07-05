import enum
import os
from datetime import datetime, timedelta
from urllib.parse import quote

from apluslms_shepherd.config import DevelopmentConfig
from apluslms_shepherd.extensions import db


class State(enum.Enum):
    VALID = 1
    NO_MATCHING_PAIR = 2
    NO_ACCESS_TO_REMOTE = 3


class CRUD(object):
    def save(self):
        db.session.add(self)
        return db.session.commit()

    def delete(self):
        db.session.delete(self)
        return db.session.commit()


class GitRepository(db.Model, CRUD):
    """Define a Git repository, for SSH key management"""
    origin = db.Column(db.String(255), primary_key=True)
    courses = db.relationship('CourseInstance', backref='git_repository', lazy='dynamic')
    public_key = db.Column(db.Text)
    last_validation = db.Column(db.DateTime)
    state = db.Column(db.Enum(State))

    @property
    def folder_name(self):
        return quote(self.origin)

    @property
    def private_key_path(self):
        return os.path.join(DevelopmentConfig.REPO_KEYS_PATH, self.folder_name)

    @property
    def bare_repo_path(self):
        return os.path.join(DevelopmentConfig.REPO_KEYS_PATH, self.folder_name)

    @property
    def need_validation(self, period=None):
        if period is None or not isinstance(period, timedelta):
            ret = (datetime.utcnow() - self.last_validation) > timedelta(days=0, hours=0, seconds=1)
        else:
            ret = (datetime.utcnow() - self.last_validation) > period
        return ret
