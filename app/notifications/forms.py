from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import BooleanField, IntegerField, StringField, SubmitField
from wtforms.validators import DataRequired, NumberRange, Optional


class NotificationScanForm(FlaskForm):
    inventory_overdue_days = IntegerField(
        "Inventário vencido após quantos dias?",
        validators=[DataRequired(), NumberRange(min=1, max=365)],
        default=30,
    )
    transfer_pending_days = IntegerField(
        "Transferência pendente após quantos dias?",
        validators=[DataRequired(), NumberRange(min=0, max=365)],
        default=1,
    )
    submit = SubmitField("Executar varredura")


class NotificationSendForm(FlaskForm):
    limit = IntegerField(
        "Limite de e-mails",
        validators=[DataRequired(), NumberRange(min=1, max=500)],
        default=50,
    )
    dry_run = BooleanField("Simular envio")
    submit = SubmitField("Enviar pendentes")


class NotificationFilterForm(FlaskForm):
    q = StringField("Busca", validators=[Optional()])
    status = StringField("Status", validators=[Optional()])
