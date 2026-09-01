from __future__ import annotations

from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileSize
from wtforms import (
    DateTimeLocalField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Length, Optional, Regexp

from app.models.enums import OccurrenceStatus, OccurrenceType

CODE_REGEX = r"^[A-Za-z0-9_.-]+$"
ALLOWED_EVIDENCE_EXTENSIONS = ("pdf", "png", "jpg", "jpeg", "webp")


class OccurrenceForm(FlaskForm):
    codigo_ferramenta = StringField(
        "Código interno da ferramenta",
        validators=[
            DataRequired(),
            Length(max=80),
            Regexp(
                CODE_REGEX,
                message="Use apenas letras, números, ponto, hífen ou underline.",
            ),
        ],
    )
    tipo_ocorrencia = SelectField(
        "Tipo de ocorrência",
        choices=OccurrenceType.choices(),
        validators=[DataRequired()],
    )
    motivo = StringField("Motivo", validators=[DataRequired(), Length(min=5, max=255)])
    descricao = TextAreaField(
        "Descrição", validators=[DataRequired(), Length(min=10, max=3000)]
    )
    fato_em = DateTimeLocalField(
        "Data/hora do fato",
        validators=[Optional()],
        format="%Y-%m-%dT%H:%M",
    )
    submit = SubmitField("Registrar ocorrência")


class OccurrenceDecisionForm(FlaskForm):
    motivo = TextAreaField(
        "Motivo/decisão", validators=[DataRequired(), Length(min=5, max=1500)]
    )
    submit = SubmitField("Confirmar")


class OccurrenceResolveForm(FlaskForm):
    observacoes_resolucao = TextAreaField(
        "Observações de resolução",
        validators=[DataRequired(), Length(min=5, max=1500)],
    )
    submit = SubmitField("Resolver ocorrência")


class OccurrenceAttachmentForm(FlaskForm):
    arquivo = FileField(
        "Anexo ou foto",
        validators=[
            FileAllowed(ALLOWED_EVIDENCE_EXTENSIONS, "Envie PDF ou imagem."),
            FileSize(
                max_size=8 * 1024 * 1024, message="Arquivo deve ter no máximo 8 MB."
            ),
        ],
    )
    descricao = StringField(
        "Descrição do anexo", validators=[Optional(), Length(max=255)]
    )
    submit = SubmitField("Enviar anexo")


class OccurrenceFilterForm(FlaskForm):
    status = SelectField("Status", choices=[("", "Todos")] + OccurrenceStatus.choices())
