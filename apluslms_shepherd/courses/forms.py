from wtforms import Form, StringField, validators, TextAreaField, BooleanField,SelectField
from wtforms.widgets import html_params


class CourseCreateForm(Form):
    key = StringField('Course Key', [validators.InputRequired(),validators.Length(max=50)])
    instance_key = StringField('First Instance Key', [validators.InputRequired(),validators.Length(max=50)])
    name = StringField('Course Name', [validators.InputRequired(),validators.Length(min=1,max=50)])
    git_origin = StringField([validators.InputRequired(),validators.Length(max=255)])
    change_all = BooleanField('Change git origin to all instance?')
    branch = StringField('First Instance Branch', [validators.InputRequired(),validators.Length(max=50)])
    # The options of the identity group which has the permission to create new courses 
    # and the current user is the member of
    identity = SelectField('Identity',choices=[(-1, "---")], coerce=int) 
    # The options of the group that owns the course
    owner_group = SelectField('Owner Group',choices=[(-1, "---")],coerce=int)
    

class InstanceForm(Form):
    key = StringField('Instance Key', [validators.InputRequired(),validators.Length(max=50)])
    git_origin = StringField('Git Origin', [validators.InputRequired(),validators.Length(max=255)])
    secret_token = StringField('Secret Token', [validators.length(max=127), validators.optional(True)],
                               render_kw={"placeholder": "If no secret token set for GitHub/Gitlab webhook, leave this empty."})
    branch = StringField('Instance Branch', [validators.Length(max=50)])
    config_filename = StringField('Roman Config File', [validators.length(max=127), validators.optional(True)],
                                  render_kw={"placeholder" : "To use default filename(course.yml), leave this empty."})


class CourseEditForm(Form):
    key = StringField('Course Key', [validators.InputRequired(),validators.Length(max=50)])
    name = StringField('Course Name', [validators.InputRequired(),validators.Length(min=1,max=50)])
    git_origin = StringField([validators.Optional(),validators.Length(max=255)])
    identity = SelectField('Identity',choices=[(-1, "---")], coerce=int) 
    change_all = BooleanField('Change git origin to all instance?')
