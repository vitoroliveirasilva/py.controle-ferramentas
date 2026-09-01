from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import EmailField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Optional


# Desenvolvimento: Formulário de login para ambiente de desenvolvimento, sem chamada à Microsoft
class DevLoginForm(FlaskForm):

    email = EmailField(
        "E-mail corporativo",
        validators=[DataRequired(), Email(), Length(max=255)],
    )
    nome = StringField("Nome", validators=[Optional(), Length(max=180)])
    microsoft_oid = StringField(
        "Microsoft OID", validators=[Optional(), Length(max=128)]
    )
    submit = SubmitField("Entrar em modo desenvolvimento")
