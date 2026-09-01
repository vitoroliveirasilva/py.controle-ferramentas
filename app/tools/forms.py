from __future__ import annotations

from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from wtforms import BooleanField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional, Regexp

from app.models.enums import ToolCriticality, ToolStatus

CODE_REGEX = r"^[A-Za-z0-9_.-]+$"


class ToolForm(FlaskForm):
    codigo_interno = StringField(
        "Código interno",
        validators=[
            DataRequired(),
            Length(max=80),
            Regexp(
                CODE_REGEX,
                message="Use apenas letras, números, ponto, hífen ou underline.",
            ),
        ],
    )
    nome = StringField("Nome", validators=[DataRequired(), Length(max=180)])
    descricao = TextAreaField("Descrição", validators=[Optional(), Length(max=1500)])
    id_categoria = SelectField("Categoria", coerce=int, validators=[DataRequired()])
    status = SelectField(
        "Status", choices=ToolStatus.choices(), validators=[DataRequired()]
    )
    criticidade = SelectField(
        "Criticidade", choices=ToolCriticality.choices(), validators=[DataRequired()]
    )
    ativo_imobilizado = StringField(
        "Ativo imobilizado", validators=[Optional(), Length(max=80)]
    )
    numero_serie = StringField(
        "Número de série", validators=[Optional(), Length(max=120)]
    )
    marca = StringField("Marca", validators=[Optional(), Length(max=120)])
    modelo = StringField("Modelo", validators=[Optional(), Length(max=120)])
    controle_individual = BooleanField("Controle individual")
    requer_calibracao = BooleanField("Exige calibração")
    ativo = BooleanField("Ferramenta ativa")
    observacoes = TextAreaField(
        "Observações", validators=[Optional(), Length(max=1500)]
    )
    motivo = TextAreaField(
        "Motivo da alteração crítica",
        validators=[Optional(), Length(max=1000)],
        description=(
            "Obrigatório ao alterar código, ativo, série, status, categoria ou flags críticas."
        ),
    )
    submit = SubmitField("Salvar ferramenta")


class ToolReferencePhotoForm(FlaskForm):
    foto = FileField("Foto de referência")
    motivo = TextAreaField(
        "Motivo/observação",
        validators=[Optional(), Length(max=1000)],
        description="Informe uma observação quando a troca da foto tiver impacto operacional.",
    )
    submit = SubmitField("Salvar foto")


class ToolLookupForm(FlaskForm):
    codigo = StringField(
        "Código, ativo ou série",
        validators=[DataRequired(), Length(max=120)],
        description="Leia o QR Code/código de barras ou digite o identificador da ferramenta.",
    )
    submit = SubmitField("Buscar ferramenta")
