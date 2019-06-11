from apluslms_shepherd.extensions import db
from sqlalchemy_mptt.mixins import BaseNestedSets
import enum
import re

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
# For Group model and CourseRepository model 
gc_table = db.Table('gc_table', db.Model.metadata,
                    db.Column('group_id', db.Integer, db.ForeignKey('group.id')),
                    db.Column('course_key', db.String, db.ForeignKey('course_repository.key'))
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
    permissions = db.relationship("GroupPermission", secondary=gp_table,
                                  backref=db.backref('groups', lazy='dynamic'))
    self_admin = db.Column(db.Boolean,default=True)

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
    self_admin = 1
    subgroups = 2
    courses = 3
    

class GroupPermission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.Enum(PermType))


class CreateGroupPerm(db.Model):
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'),primary_key=True)
    target_group_id = db.Column(db.Integer, db.ForeignKey('group.id'),primary_key=True)
    group = db.relationship('Group',foreign_keys=[group_id],backref=db.backref("group_perm", 
                            uselist=False,cascade='all,delete'))
    target_group = db.relationship('Group',foreign_keys=[target_group_id],
                                backref=db.backref("group_perm_as_target", 
                                uselist=False,cascade='all,delete'))


class CreateCoursePerm(db.Model):
    id = db.Column(db.Integer,primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'))
    group = db.relationship("Group", backref=db.backref("course_permission", 
                            uselist=False,cascade='all,delete'))
    regexp = db.Column(db.Boolean,default=True)
    pattern = db.Column(db.String(30))

    def pattern_match(self,course_name):
        """Check whether the course_name meet the pattern requirement.
        """
        if self.pattern is None:  # No pattern requirement needed
            return True 
        else:
            flag = re.match(self.pattern,course_name)
            if flag:
                return True
            else:
                return False


