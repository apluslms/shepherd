import enum

from apluslms_shepherd.extensions import db


class BuildState(enum.Enum):
    NONE = 0
    PUBLISH = 1
    RUNNING = 2
    SUCCESS = 3
    FAILED = 4
    CANCELED = 5


# Roman step also included
class BuildStep(enum.Enum):
    NONE = 0
    CLONE = 1
    BUILD = 2
    DEPLOY = 3
    CLEAN = 4


class Build(db.Model):
    """A complete build process for a instance, include 4 steps"""
    course_id = db.Column(db.Integer, db.ForeignKey('course_instance.id'), primary_key=True)
    number = db.Column(db.Integer, primary_key=True)
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    result = db.Column(db.Enum(BuildState), default=0)
    instance = db.relationship('CourseInstance', backref=db.backref('builds', cascade="save-update, merge, "
                                                                                      "delete"))


class BuildLog(db.Model):
    """A single step in Build, i.e.: clone"""
    course_id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer, primary_key=True)
    step = db.Column(db.Enum(BuildStep), primary_key=True)
    roman_step = db.Column(db.String, primary_key=True, default="Roman is not running")
    result = db.Column(db.Enum(BuildState))
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    log_text = db.Column(db.Text)


# Create index for course id and build number, for faster querying.
db.Index('build_id_number', BuildLog.course_id, BuildLog.number)
