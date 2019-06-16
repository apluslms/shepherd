from wtforms import Form, StringField, validators, SelectMultipleField,SelectField
from wtforms.widgets import html_params, ListWidget, CheckboxInput 

from apluslms_shepherd.groups.utils import PERMISSION_LIST

# Widget that renders a SelectMultipleField as a collection of checkboxes 
def select_multi_checkbox(field, input_class='', **kwargs):
    kwargs.setdefault('type', 'checkbox')
    field_id = kwargs.pop('id', field.id)
    html = [u'<div %s>' % html_params(id=field_id, class_=input_class)]
    for value, label, checked in field.iter_choices():
        choice_id = u'%s-%s' % (field_id, value)
        options = dict(kwargs, name=field.name, value=value, id=choice_id)
        if checked:
            options['checked'] = 'checked'
        html.append(u'&nbsp; <input %s /> ' % html_params(**options))
        html.append(u'<label for="%s">%s</label> &nbsp;' % (field_id, label))
    html.append(u'</div>')    
    return u''.join(html)


class MultiCheckboxField(SelectMultipleField):
    widget = ListWidget(prefix_label=False)
    option_widget = CheckboxInput()


class GroupForm(Form):
    # The name of the group, e.g., 'Letech'
    name = StringField('Group name', [validators.Length(max=50)])
    # The path from the root group to the parent group,
    # e.g., 'aalto.sci.cs'
    parent_path = StringField('Parent Path', [validators.Optional(),validators.Length(max=200)])
    # The options of parent groups
    # parent_group = SelectField('Parent Group',choices=[(-1, "---")], coerce=int)
    # The permission types
    permissions = SelectMultipleField('Permisson', choices=PERMISSION_LIST,widget=select_multi_checkbox)
    # If the group is permitted to create courses, 
    # the naming constraints of course names
    course_prefix = StringField('Course Prefix', [validators.Optional()])


    

    
