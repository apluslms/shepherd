from apluslms_shepherd.extensions import db
from flask_login import UserMixin,LoginManager
from apluslms_shepherd.config import DevelopmentConfig
from sqlalchemy.schema import CheckConstraint
from sqlalchemy.orm import validates


class Member(db.Model,UserMixin):

    id = db.Column(db.Integer,primary_key=True)
    full_name = db.Column(db.String(100),nullable=False)
    display_name = db.Column(db.String(30),nullable=False)
    sorting_name = db.Column(db.String(50),nullable=False)
    email = db.Column(db.String(DevelopmentConfig.EMAIL_LENGTH), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

    def __init__(self,full_name,display_name,sorting_name,email,password):
        self.full_name = full_name
        self.display_name = display_name
        self.sorting_name = sorting_name
        self.email = email
        self.password = password
    
    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return unicode(self.id)


