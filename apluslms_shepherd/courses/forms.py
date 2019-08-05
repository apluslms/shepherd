from wtforms import Form, StringField, validators, SelectField


class CourseForm(Form):
    course_key = StringField('Course Key', [validators.InputRequired(), validators.Length(max=50)])
    instance_key = StringField('Instance Key', [validators.InputRequired(), validators.Length(max=50)])
    name = StringField('Course Name', [validators.InputRequired(), validators.Length(min=1, max=50)])
    origin = StringField('Git Repo', [validators.InputRequired(), validators.Length(max=255)])
    secret_token = StringField('Secret Token', [validators.length(max=127), validators.optional(True)],
                               render_kw={
                                   "placeholder": "If no secret token set for GitHub/Gitlab webhook, leave this empty."
                               })

    branch = StringField('Branch', [validators.InputRequired(), validators.Length(max=50)])
    config_filename = StringField('Roman Config File', [validators.length(max=127), validators.optional(True)],
                                  render_kw={"placeholder": "To use default filename(course.yml), leave this empty."})
    # The options of the identity group which has the permission to create new courses
    # and the current user is the member of
    identity = SelectField('Identity', choices=[(-1, "---")], coerce=int)
    # The options of the group that owns the course
    owner_group = SelectField('Owner Group', choices=[(-1, "---")], coerce=int)


class CourseEditForm(Form):
    key = StringField('Course Key', [validators.InputRequired(), validators.Length(max=50)])
    name = StringField('Course Name', [validators.InputRequired(), validators.Length(min=1, max=50)])
    origin = StringField([validators.Optional(), validators.Length(max=255)])
    identity = SelectField('Identity', choices=[(-1, "---")], coerce=int)