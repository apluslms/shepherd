from wtforms import Form, StringField, validators, TextAreaField, BooleanField


class GroupForm(Form):
    name = StringField('Group name', [validators.InputRequired(), validators.Length(max=50) ])
    parent_path = StringField('Parent Path', [validators.Length(max=200)])


