import enum

from apluslms_shepherd.extensions import db


class State(enum.Enum):
    PUBLISH = 1
    RUNNING = 2
    FINISHED = 3
    FAILED = 4


class Action(enum.Enum):
    CLONE = 1
    BUILD = 2
    DEPLOY = 3
    CLEAN = 4


class Build(db.Model):
    """A complete build process for a instance, include 4 steps"""
    instance_id = db.Column(db.Integer, db.ForeignKey('course_instance.id'), primary_key=True)
    number = db.Column(db.Integer, primary_key=True)
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    state = db.Column(db.Enum(State))
    action = db.Column(db.Enum(Action))


class BuildLog(db.Model):
    """A single step in Build, i.e.: clone"""
    instance_id = db.Column(db.Integer, db.ForeignKey('build.instance_id'), primary_key=True)
    number = db.Column(db.Integer, db.ForeignKey('build.number'), primary_key=True)
    action = db.Column(db.Enum(Action), primary_key=True)
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    log_text = db.Column(db.Text)
    instance = db.relationship("Build", foreign_keys=[instance_id])
    number_r = db.relationship("Build", foreign_keys=[number])
