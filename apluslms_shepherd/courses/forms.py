from wtforms import Form, StringField, validators, TextAreaField, BooleanField,SelectField
from wtforms.widgets import html_params

def select_option(field, select_class = "form-control", **kwargs):
    field_id = kwargs.pop('id', field.id)
    html = []
    html.append('<select %s>' % html_params(id=field_id, class_=select_class))
    for value, label, checked in field.iter_choices():
        choice_id = u'%s-%s' % (label, value)
        options = dict(value=value, id=choice_id)
        html.append(u'<option %s> ' % html_params(**options))
        html.append(label)
        html.append(u'</option>')
    html.append(u'</select>')            
    return u''.join(html)


class CourseForm(Form):
    key = StringField('Course Key', [validators.InputRequired(),validators.Length(max=50)])
    instance_key = StringField('First Instance Key', [validators.InputRequired(),validators.Length(max=50)])
    name = StringField('Course Name', [validators.InputRequired(),validators.Length(min=1,max=50)])
    git_origin = StringField([validators.InputRequired(),validators.Length(max=255)])
    change_all = BooleanField('Change git origin to all instance?')
    branch = StringField('First Instance Branch', [validators.InputRequired(),validators.Length(max=50)])
    identity = SelectField('Identity',coerce=int)
    owner_group = SelectField('Owner Group',coerce=int,widget=select_option)
    new_group = BooleanField('Create a new group for the course',default=False)
    parent_group =  SelectField('Parent Group',coerce=int)

class InstanceForm(Form):
    key = StringField('Instance Key', [validators.InputRequired(),validators.Length(max=50)])
    git_origin = StringField('Git Origin', [validators.InputRequired(),validators.Length(max=255)])
    secret_token = StringField('Secret Token', [validators.length(max=127), validators.optional(True)],
                               render_kw={"placeholder": "If no secret token set for GitHub/Gitlab webhook, leave this empty."})
    branch = StringField('Instance Branch', [validators.Length(max=50)])
    config_filename = StringField('Roman Config File', [validators.length(max=127), validators.optional(True)],
                                  render_kw={"placeholder" : "To use default filename(course.yml), leave this empty."})
