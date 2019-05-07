import enum

from apluslms_shepherd.extensions import db


class States(enum.Enum):
    PUBLISH = 1
    RUNNING = 2
    FINISHED = 3
    FAILED = 4


class Action(enum.Enum):
    CLONE = 1
    BUILD = 2


class Build(db.Model):
    # id = db.Column(db.Integer, autoincrement=True)
    instance_id = db.Column(db.Integer, db.ForeignKey('course_instance.id'), primary_key=True)
    course_key = db.Column(db.String(50))
    instance_key = db.Column(db.String(50))
    number = db.Column(db.Integer, primary_key=True)
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    state = db.Column(db.Enum(States))
    action = db.Column(db.Enum(Action))
    # log = db.relationship('BuildLog', backref='build', cascade="all,delete")


class BuildLog(db.Model):
    # id = db.Column(db.Integer, db.ForeignKey('build.id'))
    instance_id = db.Column(db.Integer, db.ForeignKey('build.instance_id'), primary_key=True)
    number = db.Column(db.Integer, db.ForeignKey('build.number'), primary_key=True)
    course_key = db.Column(db.String(50))
    instance_key = db.Column(db.String(50))
    action = db.Column(db.Enum(Action), primary_key=True)
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    log_text = db.Column(db.Text)
    instance = db.relationship("Build", foreign_keys=[instance_id])
    number_r = db.relationship("Build", foreign_keys=[number])
