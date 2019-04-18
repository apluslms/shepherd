from wtforms import Form, StringField, validators, TextAreaField, BooleanField


class CourseForm(Form):
    key = StringField('Course Key', [validators.Length(max=50)])
    name = StringField('Course Name', [validators.Length(max=50)])
    git_origin = StringField('Git Origin', [validators.Length(max=255)])
    change_all = BooleanField('Change git origin to all instance?')


class InstanceForm(Form):
    key = StringField('Instance Key', [validators.Length(max=50)])
    git_origin = StringField('Git Origin', [validators.Length(max=255)])
    branches = TextAreaField('Git Branches (Separate by space)', [validators.Length(max=255)])
