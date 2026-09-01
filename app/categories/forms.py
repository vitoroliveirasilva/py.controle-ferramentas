from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import BooleanField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional, Regexp

CODE_REGEX = r"^[A-Za-z0-9_.-]+$"


class CategoryForm(FlaskForm):
    codigo = StringField(
        "Código",
        validators=[
            DataRequired(),
            Length(max=50),
            Regexp(
                CODE_REGEX,
                message="Use apenas letras, números, ponto, hífen ou underline.",
            ),
        ],
    )
    nome = StringField("Nome", validators=[DataRequired(), Length(max=120)])
    descricao = TextAreaField("Descrição", validators=[Optional(), Length(max=1000)])
    ativo = BooleanField("Categoria ativa")
    controle_individual_padrao = BooleanField("Controle individual por padrão")
    requer_numero_serie = BooleanField("Exige número de série")
    requer_calibracao = BooleanField("Exige calibração")
    motivo = TextAreaField(
        "Motivo da alteração",
        validators=[Optional(), Length(max=1000)],
        description="Obrigatório ao alterar campos críticos de configuração.",
    )
    submit = SubmitField("Salvar categoria")
