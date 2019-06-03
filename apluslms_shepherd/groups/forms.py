from wtforms import Form, StringField, validators, SelectMultipleField, \
                    FormField,FieldList,SelectField
from wtforms.widgets import ListWidget, CheckboxInput,html_params

from apluslms_shepherd.groups.models import PERMISSION_LIST

def select_multi_checkbox(field, ul_class='', **kwargs):
    kwargs.setdefault('type', 'checkbox')
    field_id = kwargs.pop('id', field.id)
    html = [u'<div %s>' % html_params(id=field_id, class_=ul_class)]
    for value, label, checked in field.iter_choices():
        choice_id = u'%s-%s' % (field_id, value)
        options = dict(kwargs, name=field.name, value=value, id=choice_id)
        if checked:
            options['checked'] = 'checked'
        # html.append(u'<li><input %s /> ' % html_params(**options))
        html.append(u'&nbsp; <input %s /> ' % html_params(**options))
        # html.append(u'<label for="%s">%s</label></li>' % (field_id, label))
        html.append(u'<label for="%s">%s</label> &nbsp;' % (field_id, label))
    # html.append(u'</ul>')
    html.append(u'</div>')    
    return u''.join(html)


class MultiCheckboxField(SelectMultipleField):
    widget = ListWidget(prefix_label=False)
    option_widget = CheckboxInput()


class GroupForm(Form):
    name = StringField('Group name', [validators.InputRequired(),validators.Length(max=50)])
    parent_path = StringField('Parent Path', [validators.Length(max=200)])
    # permissions = MultiCheckboxField('Permisson Type', choices=PERMISSION_LIST)
    permissions = SelectMultipleField('Permisson', choices=PERMISSION_LIST,widget=select_multi_checkbox,)
    course_prefix = StringField('Course Prefix', [validators.Optional()])

    
