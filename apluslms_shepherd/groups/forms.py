from wtforms import Form, StringField, validators, SelectMultipleField
from wtforms.widgets import ListWidget, CheckboxInput

from apluslms_shepherd.groups.models import PERMISSION_LIST


class MultiCheckboxField(SelectMultipleField):
    widget = ListWidget(prefix_label=False)
    option_widget = CheckboxInput()


class GroupForm(Form):
    # name = StringField('Group name', [validators.InputRequired(), validators.Length(max=50) ])
    name = StringField('Group name', [validators.Length(max=50)])
    parent_path = StringField('Parent Path', [validators.Length(max=200)])
    permissions = MultiCheckboxField('Permisson Type', choices=PERMISSION_LIST)
