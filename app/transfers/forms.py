from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import SelectField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional

from app.models.enums import CustodyType, TransferType


class TransferCreateForm(FlaskForm):
    tipo_transferencia = SelectField(
        "Tipo de transferência",
        choices=TransferType.choices(),
        validators=[DataRequired()],
    )
    destino_tipo_custodia = SelectField(
        "Tipo de destino", choices=CustodyType.choices(), validators=[DataRequired()]
    )
    destino_usuario_id = SelectField(
        "Usuário destino", coerce=int, validators=[Optional()]
    )
    destino_location_id = SelectField(
        "Local destino", coerce=int, validators=[Optional()]
    )
    codigos_ferramentas = TextAreaField(
        "Ferramentas",
        validators=[DataRequired(), Length(max=4000)],
        description="Informe um código interno por linha, ou separe por vírgula/ponto e vírgula.",
    )
    motivo = TextAreaField(
        "Motivo", validators=[DataRequired(), Length(min=5, max=1500)]
    )
    observacoes = TextAreaField(
        "Observações", validators=[Optional(), Length(max=1500)]
    )
    submit = SubmitField("Solicitar transferência")


class TransferDecisionForm(FlaskForm):
    motivo = TextAreaField(
        "Motivo/observação", validators=[Optional(), Length(max=1500)]
    )
    submit = SubmitField("Confirmar")
