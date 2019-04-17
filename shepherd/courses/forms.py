from wtforms import Form, StringField, validators, TextAreaField


class CourseForm(Form):
    key = StringField('Course Key', [validators.Length(max=50)])
    name = StringField('Course Name', [validators.Length(max=50)])
    git_origin = StringField('Git Origin', [validators.Length(max=255)])


class InstanceForm(Form):
    key = StringField('Instance Key', [validators.Length(max=50)])
    branches = TextAreaField('Git Branches (Separate by space)', [validators.Length(max=255)])


