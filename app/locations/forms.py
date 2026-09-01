from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import BooleanField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional, Regexp

from app.models.enums import LocationType

CODE_REGEX = r"^[A-Za-z0-9_.-]+$"


class LocationForm(FlaskForm):
    codigo = StringField(
        "Código",
        validators=[
            DataRequired(),
            Length(max=60),
            Regexp(
                CODE_REGEX,
                message="Use apenas letras, números, ponto, hífen ou underline.",
            ),
        ],
    )
    nome = StringField("Nome", validators=[DataRequired(), Length(max=160)])
    tipo_local = SelectField(
        "Tipo de local", choices=LocationType.choices(), validators=[DataRequired()]
    )
    filial = StringField("Filial", validators=[Optional(), Length(max=120)])
    departamento = StringField("Departamento", validators=[Optional(), Length(max=120)])
    responsavel_nome = StringField(
        "Responsável", validators=[Optional(), Length(max=160)]
    )
    endereco = TextAreaField("Endereço", validators=[Optional(), Length(max=1000)])
    observacoes = TextAreaField(
        "Observações", validators=[Optional(), Length(max=1000)]
    )
    ativo = BooleanField("Local ativo")
    motivo = TextAreaField(
        "Motivo da alteração", validators=[Optional(), Length(max=1000)]
    )
    submit = SubmitField("Salvar local")
