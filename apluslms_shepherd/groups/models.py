import enum
import re

from sqlalchemy_mptt.mixins import BaseNestedSets

from apluslms_shepherd.extensions import db

# db.metadata.clear()
# Association tables for ManyToMany relationships
# For Group model and User model
gm_table = db.Table('gm_table', db.Model.metadata,
                    db.Column('group_id', db.Integer, db.ForeignKey('group.id')),
                    db.Column('user_id', db.Integer, db.ForeignKey('user.id'))
                    )
# For Group model and Permission model
gp_table = db.Table('gp_table', db.Model.metadata,
                    db.Column('group_id', db.Integer, db.ForeignKey('group.id')),
                    db.Column('permission_id', db.Integer, db.ForeignKey('group_permission.id'))
                    )
# For Group model and CourseInstance model 
gc_table = db.Table('gc_table', db.Model.metadata,
                    db.Column('group_id', db.Integer, db.ForeignKey('group.id')),
                    db.Column('course_instance_id', db.String, db.ForeignKey('course_instance.id'))
                    )


# CRUD class
class CRUD():
    def save(self):
        db.session.add(self)
        return db.session.commit()

    def delete(self):
        db.session.delete(self)
        return db.session.commit()


class Group(db.Model, BaseNestedSets, CRUD):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), index=True, nullable=False)
    members = db.relationship("User", secondary=gm_table,
                              backref=db.backref('groups', lazy='dynamic'))
    # Permissions include 'create subgroups' and 'create courses'
    permissions = db.relationship("GroupPermission", secondary=gp_table,
                                  backref=db.backref('groups', lazy='dynamic'))
    # Whether the group can manage itself (edit, delete, membership management)
    self_admin = db.Column(db.Boolean, default=True)

    def __init__(self, name, parent_id=None):
        self.name = name
        self.parent_id = parent_id

    def __repr__(self):
        if self.parent is None:
            return "Root: <Group (id={0}, name={1}, parent=None)>".format(self.id, self.name)
        else:
            return "<Group (id={0}, name={1}, parent={2})>".format(self.id, self.name,
                                                                   self.parent.name)


class PermType(enum.Enum):
    subgroups = 1
    courses = 2


class GroupPermission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.Enum(PermType))

    def __repr__(self):
        return "<Permission (type={0})>".format(self.type.name)


class CreateGroupPerm(db.Model):
    # id = db.Column(db.Integer, primary_key=True)

    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), primary_key=True)
    target_group_id = db.Column(db.Integer, db.ForeignKey('group.id'), primary_key=True)
    # The group whose members have the permission to create subgroups
    group = db.relationship('Group',
                            foreign_keys=[group_id],
                            # primaryjoin = "CreateGroupPerm.group_id == Group.id",
                            uselist=False,
                            backref=db.backref("group_perm", cascade='all,delete'))
    # The parent group of the subgroups created by the group with group_id
    target_group = db.relationship('Group',
                                   foreign_keys=[target_group_id],
                                   # primaryjoin = "CreateGroupPerm.target_group_id == Group.id",
                                   uselist=False,
                                   backref=db.backref("group_perm_as_target", cascade='all,delete'))

    def __repr__(self):
        return "<Create Group Permission (group={0}, target_group={1})>,".format(self.group,
                                                                                 self.target_group)


class CreateCoursePerm(db.Model):
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), primary_key=True)
    # The group whose members have the permission to create courses
    group = db.relationship("Group", backref=db.backref("course_permission",
                                                        uselist=False, cascade='all,delete'))
    regexp = db.Column(db.Boolean, default=True)
    # The course naming rule (a regular expression)
    pattern = db.Column(db.String(30))

    def __repr__(self):
        return "<Create Course Permission (group={0}, pattern={1})>,".format(self.group,
                                                                             self.pattern)

    def pattern_match(self, course_name):
        """Check whether the course_name meet the pattern requirement.
        """
        if self.pattern is None:  # No pattern requirement needed
            return True

        return True if re.match(self.pattern, course_name) else False


class CourseOwnerType(enum.Enum):
    admin = 1
    assistant = 2


class ManageCoursePerm(db.Model):
    course__instance_id = db.Column(db.Integer, db.ForeignKey('course_instance.id'), primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), primary_key=True)

    course_instance = db.relationship('CourseInstance', foreign_keys=[course__instance_id],
                                      uselist=False,
                                      backref=db.backref("manage_course_perm", cascade='all,delete'))
    group = db.relationship('Group', foreign_keys=[group_id],
                            uselist=False,
                            backref=db.backref("manage_course_perm", cascade='all,delete'))

    type = db.Column(db.Enum(CourseOwnerType))
