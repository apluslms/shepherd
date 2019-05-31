import enum
import re
from sqlalchemy_mptt.mixins import BaseNestedSets
from apluslms_shepherd.extensions import db

# db.metadata.clear()

gm_table = db.Table('gm_table', db.Model.metadata,
                    db.Column('group_id', db.Integer, db.ForeignKey('group.id')),
                    db.Column('user_id', db.Integer, db.ForeignKey('user.id'))
                    )

gp_table = db.Table('gp_table', db.Model.metadata,
                    db.Column('group_id', db.Integer, db.ForeignKey('group.id')),
                    db.Column('permission_id', db.Integer, db.ForeignKey('group_permission.id'))
                    )

# admin_table = db.Table('admin_table', db.Model.metadata,
#                     db.Column('group_id', db.Integer, db.ForeignKey('group.id')),
#                     db.Column('admin_group_id', db.Integer, db.ForeignKey('group.id'))
#                     )


class CRUD():
    def save(self):
        db.session.add(self)
        return db.session.commit()

    def delete(self):
        db.session.delete(self)
        return db.session.commit()


class Group(db.Model, BaseNestedSets, CRUD):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), index=True, nullable=False)
    members = db.relationship("User", secondary=gm_table,
                              backref=db.backref('groups', lazy='dynamic'))
    permissions = db.relationship("GroupPermission", secondary=gp_table,
                                  backref=db.backref('groups', lazy='dynamic'))
    self_admin = db.Column(db.Boolean,default=True)
    # admins = db.relationship("Group", secondary=admin_table, 
    #                        primaryjoin=id==admin_table.c.group_id,
    #                        secondaryjoin=id==admin_table.c.admin_group_id,
    #                     )

    def __init__(self, name, parent_id=None):
        self.name = name
        self.parent_id = parent_id

    def __repr__(self):
        if self.parent is None:
            return "Root: <Group (id={0}, name={1}, parent=None)>".format(self.id, self.name)
        else:
            return "<Group (id={0}, name={1}, parent={2})>".format(self.id, self.name,
                                                                   self.parent.name)

    # def is_admin(self, user):   

    #     # 1. there is an admin permission and the user is member of the permission's group 
    #     #    and the target_group_id is this group
    #     if self.self_admin:
    #         return True
    #     # OR:
    #     # 2. user is member of ancestors
    #     ancestors = self.path_to_root().all()
    #     for group in ancestors:
    #         if user in group.members:
    #             return True


# Group and AdminOfGroup: Many To Many 
# class GroupAdmin(db.Model):
#     group_id = db.Column(db.Integer, db.ForeignKey('group.id'))
#     # admin_id = db.Column(db.Integer, db.ForeignKey('group.id'))
#     groups = db.relationship("Group", secondary=admin_table,
#                                   backref=db.backref('admins', lazy='dynamic'))


PERM_TYPE = {'self_admin':'self-administrator',
            'groups': 'manage subgroups','courses': 'create courses'}
PERMISSION_LIST = list(perm_tuple for perm_tuple in PERM_TYPE.items())


class PermType(enum.Enum):
    self_admin = 1
    groups = 2
    courses = 3
    

class GroupPermission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.Enum(PermType))


# class CreateGroupPerm:
    # group_id = db.Column(db.Integer, db.ForeignKey('group.id'))
    # parent_group = foreign ForeignKey
    # self_admin = db.Column(db.boolean,default=True)
    # maybe: pattern = None or "cs-*" or "^cs-[a-c][0-9]+$" # fnmatch.fnmatch vs. re.match


class CreateCoursePerm(db.Model):
    id = db.Column(db.Integer,primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'))
    group = db.relationship("Group", backref=db.backref("course_permission", uselist=False))
    regexp = db.Column(db.Boolean,default=True)
    pattern = db.Column(db.String(30))

    def pattern_match(self,course_name):
        # None or "cs-*" or "^cs-[a-c][0-9]+$" # fnmatch.fnmatch vs. re.match
        if self.pattern is None:
            return True

        return re.match(self.pattern,course_name)


