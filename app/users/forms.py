from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import BooleanField, EmailField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, Optional


class UserAdminForm(FlaskForm):
    email = EmailField(
        "E-mail corporativo", validators=[DataRequired(), Email(), Length(max=255)]
    )
    nome = StringField("Nome", validators=[DataRequired(), Length(max=180)])
    microsoft_oid = StringField(
        "Microsoft OID", validators=[Optional(), Length(max=128)]
    )
    ativo = BooleanField("Usuário ativo")
    bloqueado = BooleanField("Usuário bloqueado")
    bloqueio_motivo = StringField(
        "Motivo do bloqueio", validators=[Optional(), Length(max=255)]
    )
    observacoes = TextAreaField(
        "Observações", validators=[Optional(), Length(max=1500)]
    )
    motivo = TextAreaField(
        "Motivo da alteração", validators=[Optional(), Length(max=1000)]
    )
    submit = SubmitField("Salvar usuário")


class StatusReasonForm(FlaskForm):
    motivo = TextAreaField("Motivo", validators=[DataRequired(), Length(max=1000)])
    submit = SubmitField("Confirmar")
