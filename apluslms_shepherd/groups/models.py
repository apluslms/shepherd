from flask import flash
from flask_login import UserMixin, login_user, LoginManager
from apluslms_shepherd.extensions import db
from apluslms_shepherd.config import DevelopmentConfig
from sqlalchemy_mptt.mixins import BaseNestedSets
from saexttype import SlugType, ChoiceType
from slugify import slugify

from apluslms_shepherd.auth.models import User

# db.metadata.clear()

association_table = db.Table('groups_members',db.Model.metadata,
    db.Column('group_id', db.Integer, db.ForeignKey('group.id')),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'))
)

class CRUD():
    def save(self):
        db.session.add(self)
        return db.session.commit()

    def delete(self):
        db.session.delete(self)
        return db.session.commit()


class Group(db.Model, BaseNestedSets, CRUD):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), index=True,nullable=False)
    members = db.relationship("User", secondary=association_table,backref='group')

    def __init__(self,name,parent_id=None):
        self.name = name
        self.parent_id = parent_id


    def __repr__(self):
        if self.parent is None:
            return "Root: <Group (id={0}, name={1}, parent=None)>".format(self.id, self.name)
        else:
            return "<Group (id={0}, name={1}, parent={2})>".format(self.id, self.name,
                                                                    self.parent.name)



    
    


