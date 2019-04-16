from wtforms import Form, StringField, validators


class CourseForm(Form):
    key = StringField('Course Key', [validators.Length(max=50)])
    name = StringField('Course Name', [validators.Length(max=50)])
    git_origin = StringField('Git Origin', [validators.Length(max=255)])
    git_branch = StringField('Git Branch', [validators.Length(max=50)])
