from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import SelectField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional

from app.models.enums import CustodyType


class CustodyAssignmentForm(FlaskForm):
    tipo_custodia = SelectField(
        "Tipo de custódia",
        choices=CustodyType.choices(),
        validators=[DataRequired()],
    )
    id_responsavel_usuario = SelectField(
        "Técnico responsável",
        coerce=int,
        validators=[Optional()],
    )
    id_location = SelectField("Local responsável", coerce=int, validators=[Optional()])
    motivo = TextAreaField(
        "Motivo", validators=[DataRequired(), Length(min=5, max=1500)]
    )
    submit = SubmitField("Salvar custódia")
