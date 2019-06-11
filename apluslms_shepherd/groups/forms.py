from wtforms import Form, StringField, validators, SelectMultipleField
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
    name = StringField('Group name', [validators.InputRequired(),validators.Length(max=50)])
    parent_path = StringField('Parent Path', [validators.Length(max=200)])
    permissions = SelectMultipleField('Permisson', choices=PERMISSION_LIST,widget=select_multi_checkbox)
    course_prefix = StringField('Course Prefix', [validators.Optional()])
    target_groups = SelectMultipleField('Parents of Subgroups',[validators.Optional()],choices=[(0,'Itself')],
                                    coerce=int,widget=select_multi_checkbox)

    
