from wtforms import Form, StringField, validators, TextAreaField, BooleanField


class CourseForm(Form):
    key = StringField('Course Key', [validators.Length(max=50)])
    instance_key = StringField('First Instance Key', [validators.Length(max=50)])
    name = StringField('Course Name', [validators.Length(max=50)])
    git_origin = StringField([validators.Length(max=255)])
    change_all = BooleanField('Change git origin to all instance?')
    branch = StringField('First Instance Branch', [validators.Length(max=50)])


class InstanceForm(Form):
    key = StringField('Instance Key', [validators.Length(max=50)])
    git_origin = StringField('Git Origin', [validators.Length(max=255)])
    secret_token = StringField('Secret Token', [validators.length(max=127), validators.optional(True)])
    branch = StringField('Instance Branch', [validators.Length(max=50)])