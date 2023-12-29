from wtforms import Form, StringField, ValidationError, IntegerField
from wtforms.validators import AnyOf, DataRequired, NumberRange

from apc_switched_rack_pdu_control_panel import app


class OutletForm(Form):
    IP = StringField(
        validators=[DataRequired(), AnyOf([d['hostname'] for d in app.config['APC_PDUS']])],
    )
    REQUESTED_STATE = StringField(
        validators=[DataRequired(), AnyOf(["ON", "OFF", "REBOOT"])],
        filters=[str.upper],
        default="",
    )

class SingleOutletForm(OutletForm):
    OUTLET = IntegerField(
        validators=[DataRequired(), NumberRange(min=0)]
    )
    REQUESTED_STATE = StringField(
        validators=[DataRequired(), AnyOf(["ON", "OFF", "REBOOT", "TOGGLE"])],
        filters=[str.upper],
        default="",
    )

class ValidPDUName():
    def __init__(self, message=None):
        if not message:
            message = 'PDU name must only contain ASCII characters'
        self.message = message

    def __call__(self, form, field):
        if not field.data or not field.data.isascii():
            raise ValidationError(self.message)

class PDURenameForm(Form):
    pduInputName = StringField(
        validators=[DataRequired(), ValidPDUName()],
    )
    IP = StringField(
        validators=[DataRequired(), AnyOf([d['hostname'] for d in app.config['APC_PDUS']])],
    )
