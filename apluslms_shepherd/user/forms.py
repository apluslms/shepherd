from wtforms import Form, StringField, validators, TextAreaField, BooleanField,PasswordField
from apluslms_shepherd.config import DevelopmentConfig


class RegistrationForm(Form):
    full_name = StringField('full name', [validators.Length(min=4, max=100)])
    display_name = StringField('display name', [validators.Length(min=4, max=30)])
    sorting_name = StringField('sorting name', [validators.Length(min=4, max=50)])
    email = StringField('Email Address', [validators.Length(min=6, max=DevelopmentConfig.EMAIL_LENGTH)])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords must match'),
        validators.Length(min=6)])
    confirm = PasswordField('Repeat Password')


class LoginForm(Form):
    email = StringField('Email Address', [validators.Length(min=6, max=DevelopmentConfig.EMAIL_LENGTH)])
    password = PasswordField('Password', validators=[validators.DataRequired()])



