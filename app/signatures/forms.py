from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import BooleanField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length


class SignatureConfirmForm(FlaskForm):
    motivo = TextAreaField(
        "Justificativa/observação da assinatura",
        validators=[DataRequired(), Length(min=5, max=2000)],
    )
    confirmar = BooleanField(
        "Confirmo que revisei as informações e assumo a responsabilidade pela ação.",
        validators=[DataRequired()],
    )
    submit = SubmitField("Assinar")
